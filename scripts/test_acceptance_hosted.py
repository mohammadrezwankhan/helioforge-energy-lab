"""Independent regression controls for the hosted study-export acceptance oracle."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

HARNESS_PATH = Path(__file__).with_name("acceptance-hosted.py")
SPEC = importlib.util.spec_from_file_location("acceptance_hosted", HARNESS_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError("Cannot load the repository hosted acceptance harness")
HARNESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HARNESS
SPEC.loader.exec_module(HARNESS)
ROOT = HARNESS_PATH.parents[1]

# Evaluate the exact JavaScript sent to Playwright, using only source data and a
# selected-series control. The oracle cannot call the application CSV helpers.
NODE_RUNNER = r"""
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash, webcrypto} from 'node:crypto';
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const context = vm.createContext({URL, Intl, structuredClone, TextEncoder, crypto: webcrypto});
let application;
if (request.mode === 'bundle') {
  vm.runInContext(fs.readFileSync(request.bundle, 'utf8'), context);
  application = context.HF;
} else {
  application = {STUDY_BUNDLE: {results: {fixture: request.result}, catalogue: []}};
}
context.window = {HF: new Proxy(application, {
  get(target, property) {
    if (property !== 'STUDY_BUNDLE' && property !== 'fmt') {
      throw new Error('Oracle called an application implementation: ' + String(property));
    }
    return target[property];
  },
})};
context.document = {querySelector: () => ({value: '0'})};
const oracle = vm.runInContext('(' + request.oracle + ')', context);
if (request.mode !== 'bundle') {
  process.stdout.write(JSON.stringify(await oracle('fixture')));
} else {
  const rows = [];
  for (const [id, result] of Object.entries(application.STUDY_BUNDLE.results)) {
    const expected = await oracle(id);
    const actual = application.toCSV(application.studyExportRows(result, result.table));
    const actualHash = createHash('sha256').update(actual).digest('hex');
    rows.push({id, expected: expected.tableCsvSha256, actual: actualHash});
  }
  process.stdout.write(JSON.stringify(rows));
}
"""


def run_oracle(result: dict[str, Any] | None = None) -> Any:
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required to verify the actual browser acceptance oracle")
    request = {
        "oracle": HARNESS.STUDY_EXPORT_ORACLE,
        "mode": "bundle" if result is None else "fixture",
        "bundle": str(ROOT / "apps/web/dist/app.js"),
        "result": result,
    }
    completed = subprocess.run(  # noqa: S603 -- fixed Node runner; repository oracle and fixture use stdin, no shell.
        [node, "--input-type=module", "--eval", NODE_RUNNER],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
        cwd=ROOT,
    )
    return json.loads(completed.stdout)


def fixture(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "study": "fixture",
        "model_version": "fixture-v1",
        "data_kind": "synthetic",
        "inputs": {"example": 2},
        "provenance": {"source": "synthetic:csv-control"},
        "equations": [],
        "limitations": ["Synthetic acceptance fixture"],
        "warnings": [],
        "sources": [],
        "evidence_sha256": "fixture-digest",
        "metrics": [],
        "series": [],
        "table": rows,
    }


def expected_csv(result: dict[str, Any], cell_texts: list[str]) -> str:
    """Encode explicit expected cell text with Python's independent CSV writer."""
    provenance = {
        "schema": "helioforge.study-export.v1",
        **{
            key: result[key]
            for key in (
                "study",
                "model_version",
                "data_kind",
                "inputs",
                "provenance",
                "equations",
                "limitations",
                "warnings",
                "sources",
                "evidence_sha256",
            )
        },
        "units": {"metrics": [], "series": []},
        "integrity_scope": (
            "Evidence digest identifies the original result JSON, not this CSV encoding; "
            "no scientific or human approval."
        ),
    }
    metadata = [
        "hf_record_kind",
        "hf_study",
        "hf_model_version",
        "hf_data_kind",
        "hf_evidence_sha256",
        "hf_provenance_json",
    ]
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(["value", *metadata])
    for index, cell in enumerate(cell_texts):
        writer.writerow(
            [
                cell,
                "observation",
                result["study"],
                result["model_version"],
                result["data_kind"],
                result["evidence_sha256"],
                json.dumps(provenance, ensure_ascii=False, separators=(",", ":")) if index == 0 else "",
            ]
        )
    return output.getvalue().removesuffix("\r\n")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class HostedCsvOracleTests(unittest.TestCase):
    def test_structured_cells_preserve_values_instead_of_object_placeholders(self) -> None:
        result = fixture([{"value": {"temperature": False, "co": True, "voc": None, "unit": "°C"}}])
        expected = expected_csv(result, ['{"temperature":false,"co":true,"voc":null,"unit":"°C"}'])
        self.assertEqual(run_oracle(result)["tableCsvSha256"], digest(expected))

    def test_recursive_array_encoding_retains_structured_members(self) -> None:
        result = fixture([{"value": [1, None, ["x", {"co": False}]]}])
        expected = expected_csv(result, ['1,,x,{"co":false}'])
        self.assertEqual(run_oracle(result)["tableCsvSha256"], digest(expected))

    def test_scalar_quoting_and_formula_defences_remain_exact(self) -> None:
        values = [None, False, 0, -5, 'a"b,c\nd', "=1+1", "+2", "-3", "@SUM(A1)", "\tx", "\rx"]
        texts = ["", "false", "0", "-5", 'a"b,c\nd', "'=1+1", "'+2", "'-3", "'@SUM(A1)", "'\tx", "'\rx"]
        result = fixture([{"value": value} for value in values])
        expected = expected_csv(result, texts)
        self.assertEqual(run_oracle(result)["tableCsvSha256"], digest(expected))

    def test_lossy_or_modified_exports_cannot_match_the_source_bound_oracle(self) -> None:
        result = fixture([{"value": {"co": True}}, {"value": {"co": False}}])
        correct = expected_csv(result, ['{"co":true}', '{"co":false}'])
        expected_hash = run_oracle(result)["tableCsvSha256"]
        self.assertEqual(expected_hash, digest(correct))
        mutations = {
            "object placeholders": expected_csv(result, ["[object Object]", "[object Object]"]),
            "changed sensor value": expected_csv(result, ['{"co":false}', '{"co":false}']),
            "missing row": expected_csv(result, ['{"co":true}']),
            "missing provenance": correct.replace('"hf_provenance_json"', '"removed_provenance"'),
            "changed metadata": correct.replace('"fixture-v1"', '"fixture-v2"'),
        }
        for name, altered in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(expected_hash, digest(altered))

    def test_all_59_frozen_study_csvs_match_the_independent_oracle(self) -> None:
        rows = run_oracle()
        self.assertEqual(len(rows), 59)
        self.assertEqual(len({row["id"] for row in rows}), 59)
        self.assertIn("pilots-offgas", {row["id"] for row in rows})
        self.assertIn("council-debate", {row["id"] for row in rows})
        for row in rows:
            with self.subTest(study=row["id"]):
                self.assertEqual(row["expected"], row["actual"])


if __name__ == "__main__":
    unittest.main()
