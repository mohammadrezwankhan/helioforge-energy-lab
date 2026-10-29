"""Browser acceptance for v1 workspace migration in an isolated loopback context."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE = ROOT / ".cloudflare" / "acceptance-20261029-f" / "site"
DEFAULT_URL = "https://127.0.0.1:4199/run/"
EXPECTED_RUNTIME = "43d880c5b042fbea578d2e245f76acf8a896af60fb4f2b7c11255dc264b8e5bf"
WORKSPACE_KEY = "hf-workspace-v3"
BACKUP_KEY = "hf-workspace-import-backup-v1"
SOURCE_SCHEMA = "helioforge.workspace.v1"
TARGET_SCHEMA = "helioforge.workspace.v2"
RECEIPT_SCHEMA = "helioforge.workspace-migration.v1"
TIMESTAMP_CHANGE = "Refreshed the workspace saved_at timestamp during migration."
STALE_RUN_LOSS = "Cleared the saved last-run ID because current inputs differ from the v1 workspace inputs."


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--site", type=Path, default=DEFAULT_SITE)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/remediation-20261029/workspace-browser-results.json")
    parser.add_argument("--expected-runtime-sha256", default=EXPECTED_RUNTIME)
    args = parser.parse_args()

    parsed = urlparse(args.url)
    if parsed.scheme != "https" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("This runner only permits HTTPS loopback URLs; certificate bypass is loopback-only.")

    checks: list[dict] = []
    browser_info: dict = {"url": args.url, "context": "isolated synthetic workspace fixture", "browser": "Playwright Chromium"}
    requests: list[str] = []
    api_attempts: list[str] = []
    remote_attempts: list[str] = []
    page_errors: list[str] = []
    console_errors: list[str] = []
    runtime_sha256: str | None = None

    def check(name: str, expected, actual, passed: bool, evidence: str = "") -> None:
        checks.append({"name": name, "status": "PASS" if passed else "FAIL", "expected": expected,
                       "actual": actual, "evidence": evidence})

    def wait_app(page) -> None:
        page.wait_for_function("() => Boolean(window.HF && window.HF.presetInputs && window.HF.initialHybridState)", timeout=15_000)

    def seed_v1(page, run_id: str, load_kw: float) -> str:
        return page.evaluate(
            """({runId, loadKw}) => {
              const hf = window.HF;
              const inputs = hf.presetInputs('hospital-island');
              inputs.load_kw = loadKw;
              const savedAt = '2026-10-28T12:00:00.000Z';
              const record = {
                schema: 'helioforge.workspace.v1', saved_at: savedAt, inputs,
                lesson_id: hf.initialHybridState().lessonId, last_run_id: runId,
                pinned_run_ids: [
                  '11111111-2222-4333-8444-555555555555',
                  '66666666-7777-4888-8999-aaaaaaaaaaaa'
                ],
                saved_setups: [{
                  id: 'setup-d85c1ad4-98b3-46e1-af53-23a202435683', name: 'Acceptance saved setup',
                  created_at: savedAt, inputs: structuredClone(inputs)
                }]
              };
              const raw = JSON.stringify(record);
              localStorage.setItem('hf-workspace-v3', raw);
              return raw;
            }""",
            {"runId": run_id, "loadKw": load_kw},
        )

    def open_workspace(page) -> None:
        page.locator('[data-champion-action="workspace"]').first.click()
        page.locator("#modal-title").get_by_text("Saved setups", exact=True).wait_for(timeout=5000)

    def export_receipt(page) -> dict:
        with page.expect_download(timeout=8000) as download_info:
            page.locator('[data-champion-action="export-workspace-migration-receipt"]').click()
        download = download_info.value
        path = download.path()
        if path is None:
            raise RuntimeError(f"Receipt download failed: {download.failure()}")
        return json.loads(Path(path).read_text(encoding="utf-8"))

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                ignore_https_errors=True,
                accept_downloads=True,
                viewport={"width": 1440, "height": 1000},
                service_workers="block",
            )
            page = context.new_page()
            origin = f"{parsed.scheme}://{parsed.netloc}"

            def route_guard(route) -> None:
                url = route.request.url
                requests.append(url)
                request_url = urlparse(url)
                if request_url.netloc != parsed.netloc or request_url.scheme != parsed.scheme:
                    remote_attempts.append(url)
                    route.abort()
                elif request_url.path.startswith("/api/"):
                    api_attempts.append(url)
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", route_guard)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

            response = page.goto(args.url, wait_until="domcontentloaded", timeout=20_000)
            if response is None:
                raise RuntimeError("The local workspace page returned no main-document response.")
            runtime_sha256 = sha256(response.body())
            browser_info.update({"chromium_version": browser.version, "runtime_sha256": runtime_sha256,
                                 "main_document_status": response.status, "origin": origin})
            check("runtime_hash_matches_candidate", args.expected_runtime_sha256, runtime_sha256,
                  response.status == 200 and runtime_sha256 == args.expected_runtime_sha256,
                  "SHA-256 of the actual /run/ main-document response bytes.")
            wait_app(page)

            first_run_id = "f6b50c62-95a4-4aa4-a3da-1a4af7709966"
            first_raw = seed_v1(page, first_run_id, 651)
            page.reload(wait_until="domcontentloaded")
            wait_app(page)
            check("v1_fixture_loaded_without_edit", {"schema": SOURCE_SCHEMA, "load_kw": 651, "last_run_id": first_run_id},
                  page.evaluate("() => { const x=JSON.parse(localStorage.getItem('hf-workspace-v3')); return {schema:x.schema,load_kw:x.inputs.load_kw,last_run_id:x.last_run_id}; }"),
                  page.evaluate("() => localStorage.getItem('hf-workspace-v3')") == first_raw)

            open_workspace(page)
            page.locator('[data-champion-action="migrate-workspace"]').click()
            page.locator("#modal-title").get_by_text("Preview workspace migration", exact=True).wait_for(timeout=5000)
            preview_text = page.locator("body").inner_text()
            preview_raw = page.evaluate("() => localStorage.getItem('hf-workspace-v3')")
            check("migration_preview_discloses_schemas_and_timestamp_change",
                  [SOURCE_SCHEMA, TARGET_SCHEMA, TIMESTAMP_CHANGE],
                  {"source": SOURCE_SCHEMA in preview_text, "target": TARGET_SCHEMA in preview_text,
                   "timestamp_change": TIMESTAMP_CHANGE in preview_text},
                  SOURCE_SCHEMA in preview_text and TARGET_SCHEMA in preview_text and TIMESTAMP_CHANGE in preview_text)
            check("preview_does_not_replace_raw_local_v1", first_raw, preview_raw, preview_raw == first_raw)
            preview_receipt = export_receipt(page)
            check("preview_receipt_is_versioned_and_lossless",
                  {"schema": RECEIPT_SCHEMA, "source_schema": SOURCE_SCHEMA, "target_schema": TARGET_SCHEMA, "losses": []},
                  {key: preview_receipt.get(key) for key in ("schema", "source_schema", "target_schema", "losses")},
                  preview_receipt.get("schema") == RECEIPT_SCHEMA
                  and preview_receipt.get("source_schema") == SOURCE_SCHEMA
                  and preview_receipt.get("target_schema") == TARGET_SCHEMA
                  and preview_receipt.get("losses") == [])

            page.locator('[data-champion-action="confirm-workspace-import"]').click()
            page.get_by_text("Workspace migration complete.", exact=False).wait_for(timeout=5000)
            migrated_raw = page.evaluate("() => localStorage.getItem('hf-workspace-v3')")
            migrated = json.loads(migrated_raw)
            backup = page.evaluate("() => localStorage.getItem('hf-workspace-import-backup-v1')")
            check("confirmed_migration_preserves_exact_v1_backup", first_raw, backup, backup == first_raw)
            preserved = {
                "schema": migrated.get("schema"), "load_kw": migrated.get("inputs", {}).get("load_kw"),
                "last_run_id": migrated.get("last_run_id"), "pinned_run_ids": migrated.get("pinned_run_ids"),
                "saved_setups": migrated.get("saved_setups"), "lesson_id": migrated.get("lesson_id"),
            }
            expected_preserved = json.loads(first_raw)
            check("confirmed_unchanged_v1_fields_and_run_pointer_preserved",
                  {"schema": TARGET_SCHEMA, "load_kw": 651, "last_run_id": first_run_id,
                   "pinned_run_ids": expected_preserved["pinned_run_ids"], "saved_setups": expected_preserved["saved_setups"],
                   "lesson_id": expected_preserved["lesson_id"]},
                  preserved,
                  migrated.get("schema") == TARGET_SCHEMA
                  and migrated.get("inputs", {}).get("load_kw") == 651
                  and migrated.get("last_run_id") == first_run_id
                  and migrated.get("pinned_run_ids") == expected_preserved["pinned_run_ids"]
                  and migrated.get("saved_setups") == expected_preserved["saved_setups"]
                  and migrated.get("lesson_id") == expected_preserved["lesson_id"])
            migration = migrated.get("migration") or {}
            check("persisted_receipt_records_schema_timestamp_and_no_losses",
                  {"schema": RECEIPT_SCHEMA, "source_schema": SOURCE_SCHEMA, "target_schema": TARGET_SCHEMA,
                   "timestamp_change": True, "losses": []},
                  {"schema": migration.get("schema"), "source_schema": migration.get("source_schema"),
                   "target_schema": migration.get("target_schema"), "timestamp_change": TIMESTAMP_CHANGE in migration.get("changes", []),
                   "losses": migration.get("losses")},
                  migration.get("schema") == RECEIPT_SCHEMA
                  and migration.get("source_schema") == SOURCE_SCHEMA
                  and migration.get("target_schema") == TARGET_SCHEMA
                  and TIMESTAMP_CHANGE in migration.get("changes", [])
                  and migration.get("losses") == [])

            page.reload(wait_until="domcontentloaded")
            wait_app(page)
            check("v2_workspace_survives_reload_byte_for_byte", migrated_raw,
                  page.evaluate("() => localStorage.getItem('hf-workspace-v3')"),
                  page.evaluate("() => localStorage.getItem('hf-workspace-v3')") == migrated_raw)
            open_workspace(page)
            reloaded_receipt = export_receipt(page)
            check("migration_receipt_survives_reload", migration, reloaded_receipt, reloaded_receipt == migration)

            second_run_id = "e8107071-3a8b-4c0a-b28b-93558cf90788"
            second_raw = seed_v1(page, second_run_id, 651)
            page.reload(wait_until="domcontentloaded")
            wait_app(page)
            load_input = page.locator('input[name="load_kw"]')
            load_input.wait_for(timeout=8000)
            load_input.fill("652")
            page.locator('[data-champion-action="workspace"]').first.click()
            page.locator("#modal-title").get_by_text("Saved setups", exact=True).wait_for(timeout=5000)
            page.locator('[data-champion-action="migrate-workspace"]').click()
            page.locator("#modal-title").get_by_text("Preview workspace migration", exact=True).wait_for(timeout=5000)
            edited_preview = page.locator("body").inner_text()
            check("editing_custom_v1_input_discloses_run_pointer_loss", STALE_RUN_LOSS,
                  STALE_RUN_LOSS in edited_preview, STALE_RUN_LOSS in edited_preview)
            edited_receipt = export_receipt(page)
            page.locator('[data-champion-action="confirm-workspace-import"]').click()
            page.get_by_text("Workspace migration complete.", exact=False).wait_for(timeout=5000)
            second_migrated_raw = page.evaluate("() => localStorage.getItem('hf-workspace-v3')")
            second_migrated = json.loads(second_migrated_raw)
            check("edited_v1_migration_clears_stale_run_id_and_records_loss",
                  {"last_run_id": None, "losses": [STALE_RUN_LOSS]},
                  {"last_run_id": second_migrated.get("last_run_id"),
                   "losses": (second_migrated.get("migration") or {}).get("losses")},
                  second_migrated.get("schema") == TARGET_SCHEMA
                  and second_migrated.get("last_run_id") is None
                  and (second_migrated.get("migration") or {}).get("losses") == [STALE_RUN_LOSS])
            check("edited_migration_preview_receipt_matches_persisted_receipt",
                  second_migrated.get("migration"), edited_receipt,
                  second_migrated.get("migration") == edited_receipt)

            open_workspace(page)
            current_raw = page.evaluate("() => localStorage.getItem('hf-workspace-v3')")
            for name, file_bytes in (
                ("unsupported-v0.json", b'{"schema":"helioforge.workspace.v0"}'),
                ("corrupt.json", b'{"schema":'),
            ):
                with page.expect_file_chooser(timeout=5000) as chooser_info:
                    page.locator('[data-champion-action="import-workspace"]').click()
                chooser_info.value.set_files({"name": name, "mimeType": "application/json", "buffer": file_bytes})
                page.wait_for_timeout(100)
                after_rejection = page.evaluate("() => localStorage.getItem('hf-workspace-v3')")
                check(f"{name}-rejected-without-replacing-v2-workspace", current_raw, after_rejection,
                      after_rejection == current_raw)

            check("browser_made_no_api_or_remote_requests", {"api_attempts": 0, "remote_attempts": 0},
                  {"api_attempts": api_attempts, "remote_attempts": remote_attempts},
                  not api_attempts and not remote_attempts)
            check("browser_had_no_page_errors", [], page_errors, not page_errors)
            check("browser_had_no_console_errors", [], console_errors, not console_errors)
            browser_info.update({"requests": requests, "api_attempts": api_attempts,
                                 "remote_attempts": remote_attempts, "page_errors": page_errors,
                                 "console_errors": console_errors,
                                 "workspace_raw_bytes": {"v1": len(first_raw.encode()), "v2": len(migrated_raw.encode()),
                                                         "edited_v1": len(second_raw.encode())}})
            context.close()
            browser.close()
    except Exception as exc:
        checks.append({"name": "browser_acceptance_completed", "status": "FAIL",
                       "expected": "all scoped browser steps completed", "actual": f"{type(exc).__name__}: {exc}",
                       "evidence": "See prior check entries for completed steps."})
        browser_info["error"] = f"{type(exc).__name__}: {exc}"

    status = "PASS" if checks and all(item["status"] == "PASS" for item in checks) else "FAIL"
    result = {
        "title": "HelioForge v1 workspace migration browser acceptance",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "site": str(args.site.resolve()),
        "browser": browser_info,
        "checks": checks,
        "summary": {
            "pass": sum(item["status"] == "PASS" for item in checks),
            "fail": sum(item["status"] == "FAIL" for item in checks),
            "runtime_sha256": runtime_sha256,
            "expected_runtime_sha256": args.expected_runtime_sha256,
        },
        "scope_note": "Isolated Playwright context with synthetic localStorage fixtures. Certificate bypass is limited to HTTPS loopback. Requests to /api/ and non-loopback origins are blocked and recorded. This is not a deployment, security, or scientific validation claim.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "pass": result["summary"]["pass"], "fail": result["summary"]["fail"],
                      "runtime_sha256": runtime_sha256, "results": str(args.output)}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
