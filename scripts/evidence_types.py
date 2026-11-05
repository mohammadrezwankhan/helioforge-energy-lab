"""Validated JSON shapes consumed by the historical acceptance finalizers.

Only fields that the finalizers inspect are constrained here. Extra evidence is
retained exactly; this reader never fills missing fields, changes counts, or
turns a missing observation into a pass.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict, cast


class EvidenceCase(TypedDict, total=False):
    test_id: str
    status: str
    check: str
    actual: object


Summary = TypedDict(
    "Summary",
    {
        "passed": int,
        "failed": int,
        "unavailable": int,
        "PASS": int,
        "FAIL": int,
        "pass": int,
        "fail": int,
        "runs": int,
        "executed": int,
        "axeViolations": int,
        "runtime_sha256": str | None,
        "catalogue": dict[str, int],
        "studies": dict[str, int],
    },
    total=False,
)


class LoadMetrics(TypedDict, total=False):
    lcp: float | None
    cls: float | None


class UnionMetric(TypedDict, total=False):
    union_ms: float | None


class EvidenceRun(TypedDict, total=False):
    profile: str
    cache: str
    status: str
    lab_lcp_budget_status: str
    interactions: list[EvidenceCase]
    metrics: LoadMetrics
    main_thread_union_metrics: dict[str, UnionMetric]


class HostedExecution(TypedDict, total=False):
    status: str
    checks: list[EvidenceCase]


class Candidate(TypedDict, total=False):
    runtime_sha256: str


class DeployedBrowser(TypedDict, total=False):
    runtime_response_sha256: str
    digest_matches_manifest: bool


class EvidenceReport(TypedDict, total=False):
    scope: str
    oracle: str
    status: str
    artifact_sha256: str
    finished_at: str
    cases: list[EvidenceCase]
    catalogue: list[EvidenceCase]
    studies: list[EvidenceCase]
    checks: list[object]
    summary: Summary
    executions: list[HostedExecution]
    runs: list[EvidenceRun]
    candidate: Candidate
    browser: DeployedBrowser
    targeted_test_run: object
    all_case_status_counts: dict[str, int]


def _record(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a JSON object with text keys")
    return value


def _text_fields(record: dict[str, object], fields: tuple[str, ...], label: str) -> None:
    for key in fields:
        if key in record and not isinstance(record[key], str):
            raise ValueError(f"{label}.{key} must be text")


def _numeric_fields(record: dict[str, object], fields: tuple[str, ...], label: str) -> None:
    for key in fields:
        if key not in record or record[key] is None:
            continue
        value = record[key]
        if type(value) not in (int, float) or not math.isfinite(cast(int | float, value)):
            raise ValueError(f"{label}.{key} must be a finite number or null")


def evidence_cases(value: object, label: str = "checks") -> list[EvidenceCase]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list of evidence records")
    for index, item in enumerate(value):
        record = _record(item, f"{label}[{index}]")
        _text_fields(record, ("test_id", "status", "check"), f"{label}[{index}]")
    return cast(list[EvidenceCase], value)


def _counts(value: object, label: str) -> None:
    record = _record(value, label)
    if any(type(count) is not int or count < 0 for count in record.values()):
        raise ValueError(f"{label} must contain nonnegative integer counts")


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"Nonfinite JSON number in acceptance evidence: {value}")


def read_evidence(path: Path) -> EvidenceReport:
    value: object = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=_reject_nonfinite)
    report = _record(value, str(path))
    _text_fields(report, ("scope", "oracle", "status", "artifact_sha256", "finished_at"), str(path))
    for key in ("cases", "catalogue", "studies"):
        if key in report:
            evidence_cases(report[key], key)
    if "checks" in report:
        checks = report["checks"]
        if not isinstance(checks, list) or any(not isinstance(item, (str, dict)) for item in checks):
            raise ValueError("checks must contain text checks or structured evidence records")
    if "summary" in report:
        summary = _record(report["summary"], "summary")
        for key in (
            "passed",
            "failed",
            "unavailable",
            "PASS",
            "FAIL",
            "pass",
            "fail",
            "runs",
            "executed",
            "axeViolations",
        ):
            if key in summary and (type(summary[key]) is not int or cast(int, summary[key]) < 0):
                raise ValueError(f"summary.{key} must be a nonnegative integer count")
        if summary.get("runtime_sha256") is not None and not isinstance(summary["runtime_sha256"], str):
            raise ValueError("summary.runtime_sha256 must be text or null")
        for key in ("catalogue", "studies"):
            if key in summary:
                _counts(summary[key], f"summary.{key}")
    if "executions" in report:
        executions = report["executions"]
        if not isinstance(executions, list):
            raise ValueError("executions must be a list")
        for index, item in enumerate(executions):
            execution = _record(item, f"executions[{index}]")
            _text_fields(execution, ("status",), "execution")
            if "checks" in execution:
                evidence_cases(execution["checks"], "execution.checks")
    if "runs" in report:
        runs = report["runs"]
        if not isinstance(runs, list):
            raise ValueError("runs must be a list")
        for index, item in enumerate(runs):
            run = _record(item, f"runs[{index}]")
            _text_fields(run, ("profile", "cache", "status", "lab_lcp_budget_status"), "run")
            if "interactions" in run:
                evidence_cases(run["interactions"], "run.interactions")
            if "metrics" in run:
                _numeric_fields(_record(run["metrics"], "run.metrics"), ("lcp", "cls"), "run.metrics")
            if "main_thread_union_metrics" in run:
                metrics = _record(run["main_thread_union_metrics"], "run.main_thread_union_metrics")
                for key, metric in metrics.items():
                    _numeric_fields(_record(metric, key), ("union_ms",), key)
    if "candidate" in report:
        _text_fields(_record(report["candidate"], "candidate"), ("runtime_sha256",), "candidate")
    if "browser" in report:
        browser = _record(report["browser"], "browser")
        _text_fields(browser, ("runtime_response_sha256",), "browser")
        if "digest_matches_manifest" in browser and type(browser["digest_matches_manifest"]) is not bool:
            raise ValueError("browser.digest_matches_manifest must be a boolean")
    if "all_case_status_counts" in report:
        _counts(report["all_case_status_counts"], "all_case_status_counts")
    return cast(EvidenceReport, report)
