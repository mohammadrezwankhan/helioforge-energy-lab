import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "verify-release.py"


class HistoricalReleaseScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="helio-release-scope-")
        self.addCleanup(self.temporary.cleanup)
        temporary_root = Path(self.temporary.name)
        self.root = temporary_root / "snapshot"
        self.root.mkdir()
        self.runner = temporary_root / "runner"
        (self.runner / "scripts").mkdir(parents=True)
        self.script = self.runner / "scripts" / SCRIPT.name
        shutil.copyfile(SCRIPT, self.script)
        catalogue = self.root / "apps/api/helioforge/data/hybrid_catalog.json"
        catalogue.parent.mkdir(parents=True)
        catalogue.write_text(json.dumps({"systems": [0] * 36, "scenarios": [0] * 24, "lessons": [0] * 36}))
        (self.root / "sample.txt").write_bytes(b"original\n")
        self.manifest = {
            "files": [{"path": "sample.txt", "sha256": hashlib.sha256(b"original\n").hexdigest()}]
        }
        self.save_manifest()

    def save_manifest(self) -> None:
        (self.runner / "RELEASE_MANIFEST.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def verify(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 -- the interpreter and script are local test fixtures.
            [sys.executable, str(self.script), "--root", str(self.root)], capture_output=True, text=True
        )

    def test_verifies_selected_snapshot(self) -> None:
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified 1 release file hashes", result.stdout)

    def test_detects_modified_snapshot_file(self) -> None:
        (self.root / "sample.txt").write_bytes(b"changed\n")
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Changed: sample.txt", result.stderr)

    def test_rejects_manifest_paths_outside_snapshot(self) -> None:
        self.manifest["files"][0]["path"] = "../outside.txt"
        self.save_manifest()
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsafe manifest path", result.stderr)


if __name__ == "__main__":
    unittest.main()
