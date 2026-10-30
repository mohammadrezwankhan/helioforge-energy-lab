"""Lightweight regression checks for the browser acceptance harness."""

import importlib.util
import sys
import unittest
from pathlib import Path


HARNESS_PATH = Path(__file__).with_name("acceptance-performance.py")
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("acceptance_performance", HARNESS_PATH)
HARNESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HARNESS
SPEC.loader.exec_module(HARNESS)


class FakePage:
    def __init__(self):
        self.page_error_listeners = []

    def on(self, event_name, handler):
        if event_name != "pageerror":
            raise AssertionError(f"unexpected event: {event_name}")
        self.page_error_listeners.append(handler)

    def remove_listener(self, event_name, handler):
        if event_name != "pageerror":
            raise AssertionError(f"unexpected event: {event_name}")
        self.page_error_listeners.remove(handler)

    def emit_page_error(self, error):
        for handler in tuple(self.page_error_listeners):
            handler(error)


class AcceptancePerformanceTests(unittest.TestCase):
    def test_lcp_budget_failure_rejects_overall_acceptance(self):
        summary = HARNESS.summarize_runs(
            [
                {
                    "status": "PASS",
                    "target_http_status": 200,
                    "runtime_sha256_matches_site": True,
                    "page_errors": [],
                    "lab_lcp_budget_status": "FAIL",
                    "interactions": [{"name": "search", "status": "PASS"}],
                }
            ],
            expected_runs=1,
            expected_interactions=1,
        )

        self.assertEqual(summary["functional_failures"], 0)
        self.assertEqual(summary["lcp_budget_failures"], 1)
        self.assertEqual(summary["acceptance_status"], "FAIL")
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(HARNESS.acceptance_exit_code(summary), 1)

    def test_failed_interaction_rejects_an_otherwise_successful_load(self):
        summary = HARNESS.summarize_runs(
            [
                {
                    "status": "PASS",
                    "target_http_status": 200,
                    "runtime_sha256_matches_site": True,
                    "page_errors": [],
                    "lab_lcp_budget_status": "PASS",
                    "interactions": [{"name": "comparison", "status": "FAIL"}],
                }
            ],
            expected_runs=1,
            expected_interactions=1,
        )

        self.assertEqual(summary["functional_failures"], 1)
        self.assertEqual(summary["lcp_budget_failures"], 0)
        self.assertEqual(summary["acceptance_status"], "FAIL")
        self.assertEqual(summary["failed"], 1)

    def test_non_200_target_response_cannot_pass_functional_acceptance(self):
        run = {
            "status": "PASS",
            "target_http_status": 201,
            "runtime_sha256_matches_site": True,
            "page_errors": [],
            "interactions": [],
        }

        self.assertFalse(HARNESS.is_http_200(201))
        self.assertFalse(HARNESS.functional_evidence_passes(run))

    def test_page_errors_are_functional_failures(self):
        run = {
            "status": "PASS",
            "target_http_status": 200,
            "runtime_sha256_matches_site": True,
            "page_errors": ["Error: uncaught application exception"],
            "interactions": [],
        }

        self.assertFalse(HARNESS.functional_evidence_passes(run))

    def test_page_error_listener_is_removed_between_cold_and_warm_runs(self):
        page = FakePage()
        cold_run = {"page_errors": []}
        warm_run = {"page_errors": []}

        cold_handler = HARNESS.register_page_error_listener(page, cold_run)
        try:
            page.emit_page_error(RuntimeError("cold failure"))
            self.assertEqual(len(page.page_error_listeners), 1)
        finally:
            HARNESS.remove_page_error_listener(page, cold_handler)

        self.assertEqual(page.page_error_listeners, [])

        warm_handler = HARNESS.register_page_error_listener(page, warm_run)
        try:
            page.emit_page_error(RuntimeError("warm failure"))
            self.assertEqual(len(page.page_error_listeners), 1)
        finally:
            HARNESS.remove_page_error_listener(page, warm_handler)

        self.assertEqual(cold_run["page_errors"], ["RuntimeError('cold failure')"])
        self.assertEqual(warm_run["page_errors"], ["RuntimeError('warm failure')"])
        self.assertEqual(page.page_error_listeners, [])

    def test_full_acceptance_set_requires_twelve_loads_and_ninety_six_interactions(self):
        runs = [
            {
                "status": "PASS",
                "target_http_status": 200,
                "runtime_sha256_matches_site": True,
                "page_errors": [],
                "lab_lcp_budget_status": "PASS",
                "interactions": [{"name": f"interaction-{index}", "status": "PASS"} for index in range(8)],
            }
            for _ in range(12)
        ]

        summary = HARNESS.summarize_runs(runs)

        self.assertEqual(summary["executed"], 12)
        self.assertEqual(summary["interactions_executed"], 96)
        self.assertTrue(summary["run_count_complete"])
        self.assertTrue(summary["interaction_count_complete"])
        self.assertEqual(summary["acceptance_status"], "PASS")

    def test_main_thread_metrics_use_the_current_document_snapshot(self):
        # Performance.getMetrics reports seconds; a page navigation resets these
        # counters, so the new document's own snapshot is already its load total.
        snapshot = [
            {"name": "ScriptDuration", "value": 0.125},
            {"name": "TaskDuration", "value": 0.250},
            {"name": "LayoutDuration", "value": 0.010},
            {"name": "RecalcStyleDuration", "value": 0.020},
        ]

        metrics = HARNESS.current_document_main_thread_metrics(snapshot)

        self.assertEqual(metrics["ScriptDuration"], 125.0)
        self.assertEqual(metrics["TaskDuration"], 250.0)
        self.assertEqual(metrics["LayoutDuration"], 10.0)
        self.assertEqual(metrics["RecalcStyleDuration"], 20.0)

    def test_runtime_response_hash_is_compared_with_the_site_artifact(self):
        expected_sha256 = "071f995fa49078621a7a97c7de20f7a3c5e57642896e97b80d25d8eea2ba4cb4"
        evidence = HARNESS.runtime_response_evidence(
            200, "http://localhost/run/", b"site artifact", expected_sha256
        )
        mismatch = HARNESS.runtime_response_evidence(
            200, "http://localhost/run/", b"different artifact", expected_sha256
        )

        self.assertEqual(evidence["runtime_response_sha256"], expected_sha256)
        self.assertTrue(evidence["runtime_sha256_matches_site"])
        self.assertFalse(mismatch["runtime_sha256_matches_site"])


if __name__ == "__main__":
    unittest.main()
