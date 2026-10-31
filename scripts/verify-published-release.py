#!/usr/bin/env python3
"""Read-only HTTP proof for one exact, receipt-bound Cloudflare Pages release.

This tool does not build, deploy, call application providers, or try alternate
browser fingerprints. A public HTTP 403 is recorded as BLOCKED and stops the
run. Supply the exact downloaded site and its CI build receipt.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zlib
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

RECEIPT_SCHEMA = "helioforge.build-receipt.v1"
EXPECTED_DATA_CHUNKS = 297
EXPECTED_INDEXABLE_PAGES = 9
MAX_RESPONSE_BYTES = 30 * 1024 * 1024
PROVIDER_INSTRUCTIONS = {"_headers", "_redirects"}
MISSING_PATH = "/.well-known/helioforge-acceptance-20261030-real-404"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_http_body(data: bytes, content_encoding: str | None) -> bytes:
    """Decode HTTP transfer content encodings before comparing site bytes."""
    if not content_encoding:
        return data
    result = data
    for encoding in reversed([item.strip().lower() for item in content_encoding.split(",") if item.strip()]):
        if encoding in {"identity", ""}:
            continue
        if encoding in {"gzip", "x-gzip"}:
            result = gzip.decompress(result)
        elif encoding == "deflate":
            try:
                result = zlib.decompress(result)
            except zlib.error:
                result = zlib.decompress(result, -zlib.MAX_WBITS)
        else:
            raise ValueError(f"unsupported HTTP content encoding: {encoding}")
    return result


def route_for_site_file(relative: str) -> str | None:
    """Map a packaged file to its public route; instruction files are not assets."""
    relative = relative.replace("\\", "/")
    if relative in PROVIDER_INSTRUCTIONS or relative == "404.html":
        return None
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return "/" + quote(relative[: -len("index.html")], safe="/!$&'()*+,;=:@-._~")
    return "/" + quote(relative, safe="/!$&'()*+,;=:@-._~")


class NoRedirectHandler(HTTPRedirectHandler):
    """Expose redirects to the caller so each status and Location is retained."""

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class PageFactsParser(HTMLParser):
    """Collect canonical/robots metadata and exact inline script text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.robots: list[str] = []
        self.inline_scripts: list[dict[str, str]] = []
        self._script: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonicals.append(values.get("href", ""))
        if tag.lower() == "meta" and values.get("name", "").lower() == "robots":
            self.robots.append(values.get("content", ""))
        if tag.lower() == "script":
            self._script = {"type": values.get("type", "").lower(), "src": values.get("src", ""), "text": ""}

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._script is not None:
            if not self._script["src"]:
                self.inline_scripts.append(self._script)
            self._script = None


def inline_csp_tokens(parser: PageFactsParser) -> list[str]:
    tokens = []
    for script in parser.inline_scripts:
        if not script["text"].strip():
            continue
        digest = base64.b64encode(hashlib.sha256(script["text"].encode("utf-8")).digest()).decode("ascii")
        tokens.append("'sha256-" + digest + "'")
    return tokens


def read_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"invalid JSON numeric constant {value}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def inventory(site: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for item in sorted(site.rglob("*")):
        if item.is_symlink():
            raise ValueError(f"site contains a symlink: {item.relative_to(site).as_posix()}")
        if item.is_file():
            relative = item.relative_to(site).as_posix()
            result[relative] = item.read_bytes()
    return result


def check_receipt(site: Path, receipt_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, bytes]]:
    checks: list[dict[str, Any]] = []
    files = inventory(site)
    receipt = read_json(receipt_path)
    checks.append(check("receipt_schema", RECEIPT_SCHEMA, receipt.get("schema"), receipt.get("schema") == RECEIPT_SCHEMA))
    ci_identity = {"environment": "CI", "ci_run_id_present": True, "ci_attempt_present": True}
    ci_actual = {"environment": receipt.get("environment"), "ci_run_id_present": bool(receipt.get("ci_run_id")),
                 "ci_attempt_present": bool(receipt.get("ci_attempt"))}
    checks.append(check("receipt_is_from_ci_run", ci_identity, ci_actual, ci_actual == ci_identity))

    expected_rows = receipt.get("files")
    receipt_files: dict[str, dict[str, Any]] = {}
    malformed = not isinstance(expected_rows, list)
    if isinstance(expected_rows, list):
        for row in expected_rows:
            if not isinstance(row, dict) or not isinstance(row.get("path"), str) or row["path"] in receipt_files:
                malformed = True
                continue
            receipt_files[row["path"]] = row
    expected_names = sorted(receipt_files)
    actual_names = sorted(files)
    file_inventory_matches = not malformed and expected_names == actual_names
    checks.append(check("receipt_file_inventory_matches_site", actual_names, expected_names,
                        file_inventory_matches, detail="Build receipt lists every site file, including _headers and _redirects."))
    byte_mismatches = []
    if not malformed:
        for name in sorted(set(files) & set(receipt_files)):
            actual_bytes = len(files[name])
            actual_hash = sha256(files[name])
            row = receipt_files[name]
            if row.get("bytes") != actual_bytes or row.get("sha256") != actual_hash:
                byte_mismatches.append({"path": name, "expected_bytes": row.get("bytes"), "actual_bytes": actual_bytes,
                                        "expected_sha256": row.get("sha256"), "actual_sha256": actual_hash})
    checks.append(check("site_file_bytes_match_ci_receipt", [], byte_mismatches, not byte_mismatches and not malformed))

    facts = {}
    facts_error = None
    try:
        facts = json.loads(files["app.json"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        facts_error = f"{type(exc).__name__}: {exc}"
    runtime = files.get("run/index.html", b"")
    runtime_hash = sha256(runtime)
    expected_runtime = receipt.get("runtime_sha256")
    actual_runtime = {"site_runtime_sha256": runtime_hash, "receipt_runtime_sha256": expected_runtime,
                      "app_json_runtimeSha256": facts.get("runtimeSha256") if isinstance(facts, dict) else None,
                      "app_json_parse_error": facts_error}
    runtime_match = (not facts_error and runtime_hash == expected_runtime and isinstance(facts, dict)
                     and facts.get("runtimeSha256") == runtime_hash)
    checks.append(check("runtime_matches_site_manifest_and_ci_receipt",
                        {"same_sha256": True}, actual_runtime, runtime_match,
                        detail="SHA-256 is computed from exact decoded file/HTTP body bytes without newline normalization."))
    checks.append(source_identity_check(facts, receipt))
    return checks, receipt, files


def check(name: str, expected: Any, actual: Any, passed: bool, detail: str = "") -> dict[str, Any]:
    row = {"check": name, "status": "PASS" if passed else "FAIL", "expected": expected, "actual": actual}
    if detail:
        row["detail"] = detail
    return row


def source_identity_check(facts: Any, receipt: dict[str, Any]) -> dict[str, Any]:
    base_commit = receipt.get("source_base_commit")
    source_revision = facts.get("sourceRevision") if isinstance(facts, dict) else None
    valid_base = isinstance(base_commit, str) and re.fullmatch(r"[0-9a-fA-F]{40}", base_commit) is not None
    valid_revision = isinstance(source_revision, str) and re.fullmatch(r"[0-9a-fA-F]{40}", source_revision) is not None
    receipt_clean = receipt.get("working_tree_dirty") is False
    facts_clean = isinstance(facts, dict) and facts.get("sourceTreeDirty") is False
    passed = valid_base and valid_revision and source_revision == base_commit and receipt_clean and facts_clean
    return check("ci_source_identity_is_clean_and_bound",
                 {"same_40_hex_commit": True, "receipt_working_tree_dirty": False, "app_sourceTreeDirty": False},
                 {"source_base_commit": base_commit, "source_revision": source_revision,
                  "source_base_commit_valid_sha1": valid_base, "source_revision_valid_sha1": valid_revision,
                  "receipt_working_tree_dirty": receipt.get("working_tree_dirty"),
                  "app_sourceTreeDirty": facts.get("sourceTreeDirty") if isinstance(facts, dict) else None}, passed)


class Blocked(Exception):
    def __init__(self, message: str, records: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.records = records or []


class HttpClient:
    def __init__(self, base_url: str, out: Path, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.origin = urlsplit(base_url).scheme + "://" + urlsplit(base_url).netloc
        self.out = out
        self.timeout = timeout
        self.opener = build_opener(NoRedirectHandler())
        self.count = 0
        self.records: list[dict[str, Any]] = []

    def get(self, url: str, label: str) -> dict[str, Any]:
        self.count += 1
        # Cloudflare Pages rejects urllib's library-default identifier with 1010.
        # Identify this application honestly; never impersonate a browser.
        request = Request(url, method="GET", headers={
            "Accept-Encoding": "identity",
            "User-Agent": "HelioForge-Release-Verification/1.0 (+https://github.com/mohammadrezwankhan/helioforge-energy-lab)",
        })
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except HTTPError as exc:
            response = exc
        except (URLError, TimeoutError, OSError) as exc:
            record = {"request_url": url, "label": label, "status": "BLOCKED", "error": f"{type(exc).__name__}: {exc}"}
            self.records.append(record)
            raise Blocked(record["error"], self.records) from exc
        with response:
            status = int(response.status)
            headers = {key.lower(): value for key, value in response.headers.items()}
            header_pairs = list(response.headers.items())
            encoded = response.read(MAX_RESPONSE_BYTES + 1)
        if len(encoded) > MAX_RESPONSE_BYTES:
            record = {"request_url": url, "label": label, "status": "FAIL", "error": "response exceeded configured size limit"}
            self.records.append(record)
            raise RuntimeError(record["error"])
        try:
            body = decode_http_body(encoded, headers.get("content-encoding"))
        except Exception as exc:
            record = {"request_url": url, "label": label, "status": "FAIL", "error": f"decode failed: {type(exc).__name__}: {exc}"}
            self.records.append(record)
            raise RuntimeError(record["error"]) from exc
        stem = f"{self.count:04d}-{re.sub(r'[^a-zA-Z0-9._-]+', '-', label).strip('-')[:72] or 'response'}"
        body_path = self.out / "responses" / f"{stem}.body"
        headers_path = self.out / "responses" / f"{stem}.headers.json"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_bytes(body)
        headers_path.write_text(json.dumps({"request_url": url, "status": status, "headers": headers,
                                            "header_pairs": header_pairs,
                                            "encoded_sha256": sha256(encoded), "decoded_sha256": sha256(body),
                                            "decoded_bytes": len(body)}, indent=2), encoding="utf-8")
        record = {"request_url": url, "label": label, "status": status, "headers": headers,
                  "header_pairs": header_pairs,
                  "decoded_sha256": sha256(body), "decoded_bytes": len(body),
                  "body_file": body_path.relative_to(self.out).as_posix(),
                  "headers_file": headers_path.relative_to(self.out).as_posix()}
        self.records.append(record)
        if status == 403:
            record["disposition"] = "BLOCKED; stopped after ordinary HTTP access denial; no alternate fingerprint attempted"
            raise Blocked(f"HTTP 403 at {url}", self.records)
        return {"status": status, "headers": headers, "body": body, "url": url, "record": record}

    def follow(self, url: str, label: str, max_redirects: int = 5) -> dict[str, Any]:
        current = url
        chain = []
        for _ in range(max_redirects + 1):
            result = self.get(current, label if not chain else label + "-redirect")
            if result["status"] not in {301, 302, 303, 307, 308}:
                result["redirect_chain"] = chain
                return result
            location = result["headers"].get("location")
            if not location:
                result["redirect_chain"] = chain
                return result
            chain.append({"status": result["status"], "from": current, "location": location})
            next_url = urljoin(current, location)
            target = urlsplit(next_url)
            origin = urlsplit(self.origin)
            if target.scheme != "https" or target.netloc != origin.netloc:
                result["redirect_chain"] = chain
                return result
            current = next_url
        raise RuntimeError(f"redirect limit exceeded while requesting {url}")


def sitemap_urls(data: bytes) -> list[str]:
    root = ET.fromstring(data)
    return [element.text or "" for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "loc"]


def find_webpage_urls(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, list):
        for item in node:
            found.extend(find_webpage_urls(item))
    elif isinstance(node, dict):
        kind = node.get("@type")
        if (kind == "WebPage" or isinstance(kind, list) and "WebPage" in kind) and isinstance(node.get("url"), str):
            found.append(node["url"])
        for key, value in node.items():
            if key not in {"@type", "url"}:
                found.extend(find_webpage_urls(value))
    return found


def normalize_location(location: str, current_url: str) -> tuple[str, str, str]:
    parsed = urlsplit(urljoin(current_url, location))
    return parsed.scheme, parsed.netloc, parsed.path


def verify_redirect(client: HttpClient, path: str, destination: str, status: int, label: str,
                    query: str = "") -> dict[str, Any]:
    url = client.base_url + path + (("?" + query) if query else "")
    response = client.get(url, label)
    location = response["headers"].get("location", "")
    loc_scheme, loc_netloc, loc_path = normalize_location(location, url) if location else ("", "", "")
    expected_path = destination
    if query:
        expected_query = urlsplit(location).query
    else:
        expected_query = urlsplit(location).query
    passed = (response["status"] == status and bool(location) and loc_path == expected_path
              and loc_netloc in {"", urlsplit(client.base_url).netloc}
              and (not query or expected_query == query))
    return check(label, {"status": status, "location_path": expected_path, "query": query},
                 {"status": response["status"], "location": location, "location_scheme": loc_scheme,
                  "location_host": loc_netloc, "location_path": loc_path, "query": expected_query}, passed)


def verify_release(base_url: str, site: Path, files: dict[str, bytes], facts: dict[str, Any], out: Path,
                   timeout: float, request_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    client = HttpClient(base_url, out, timeout)
    client.records = request_records
    origin = client.origin

    # Begin with the public manifest. Any ordinary HTTP 403 stops all probing.
    manifest_response = client.follow(origin + "/app.json", "app-json")
    manifest_body = manifest_response["body"]
    remote_facts = json.loads(manifest_body.decode("utf-8")) if manifest_response["status"] == 200 else {}
    checks.append(check("public_app_json_matches_ci_site", sha256(files["app.json"]), sha256(manifest_body),
                        manifest_response["status"] == 200 and manifest_body == files["app.json"]))
    checks.append(check("public_manifest_runtime_hash_matches_site_manifest",
                        facts.get("runtimeSha256"), remote_facts.get("runtimeSha256"),
                        facts.get("runtimeSha256") == remote_facts.get("runtimeSha256")))

    routes: dict[str, tuple[str, bytes]] = {}
    for name, data in sorted(files.items()):
        route = route_for_site_file(name)
        if route is not None:
            if route in routes:
                checks.append(check("site_route_mapping_unique", "unique route", {"route": route, "files": [routes[route][0], name]}, False))
            else:
                routes[route] = (name, data)
    fetched: dict[str, dict[str, Any]] = {"/app.json": manifest_response}
    file_rows = []
    for route, (name, expected) in sorted(routes.items()):
        if route == "/app.json":
            result = manifest_response
        else:
            result = client.follow(origin + route, "site-" + name)
        fetched[route] = result
        passed = result["status"] == 200 and result["body"] == expected
        file_rows.append({"path": name, "route": route, "http_status": result["status"],
                          "final_url": result["url"], "expected_bytes": len(expected), "actual_bytes": len(result["body"]),
                          "expected_sha256": sha256(expected), "actual_sha256": sha256(result["body"]),
                          "status": "PASS" if passed else "FAIL"})
    checks.append(check("all_public_site_file_responses_match_exact_ci_bytes",
                        {"public_files": len(routes), "provider_instruction_files_excluded": sorted(PROVIDER_INSTRUCTIONS)},
                        {"public_files": len(file_rows), "passed": sum(row["status"] == "PASS" for row in file_rows),
                         "failed": sum(row["status"] == "FAIL" for row in file_rows)},
                        len(file_rows) == len(routes) and all(row["status"] == "PASS" for row in file_rows)))
    (out / "site-file-responses.json").write_text(json.dumps(file_rows, indent=2), encoding="utf-8")

    runtime_http = fetched.get("/run/")
    expected_runtime_hash = facts.get("runtimeSha256")
    actual_runtime_hash = sha256(runtime_http["body"]) if runtime_http is not None else None
    checks.append(check("public_runtime_http_bytes_match_manifest_and_ci_bound_site",
                        expected_runtime_hash, actual_runtime_hash,
                        runtime_http is not None and runtime_http["status"] == 200
                        and expected_runtime_hash == actual_runtime_hash,
                        detail="The site manifest digest was already compared to the exact CI receipt during preflight."))

    # The asset list and data index are distinct public bindings; check all 297 chunks.
    index_bytes = files.get("run/data-index.json")
    runtime_data = facts.get("runtimeDataManifest") if isinstance(facts, dict) else None
    asset_rows = runtime_data.get("assets") if isinstance(runtime_data, dict) else None
    index_value: dict[str, Any] = {}
    index_error = None
    try:
        if index_bytes is None:
            raise FileNotFoundError("run/data-index.json missing from receipt-bound site")
        index_value = json.loads(index_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        index_error = f"{type(exc).__name__}: {exc}"
    refs: dict[str, dict[str, Any]] = {}
    if isinstance(index_value, dict):
        for section_name in ("hybrid", "workspaces"):
            section = index_value.get(section_name, {})
            if isinstance(section, dict):
                for entry in section.values():
                    if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                        refs[entry["path"]] = entry
    asset_by_path = {item.get("path"): item for item in asset_rows if isinstance(item, dict) and isinstance(item.get("path"), str)} if isinstance(asset_rows, list) else {}
    chunks = []
    for path, reference in sorted(refs.items()):
        site_path = "run/" + path
        local_body = files.get(site_path)
        expected_hash = reference.get("sha256")
        expected_bytes = reference.get("bytes")
        local_valid = (local_body is not None and sha256(local_body) == expected_hash and len(local_body) == expected_bytes
                       and asset_by_path.get(path, {}).get("sha256") == expected_hash
                       and asset_by_path.get(path, {}).get("bytes") == expected_bytes)
        route = route_for_site_file(site_path)
        remote = fetched.get(route or "")
        remote_valid = remote is not None and remote["status"] == 200 and sha256(remote["body"]) == expected_hash and len(remote["body"]) == expected_bytes
        chunks.append({"path": path, "http_route": route, "expected_sha256": expected_hash,
                       "local_sha256": sha256(local_body) if local_body is not None else None,
                       "remote_sha256": sha256(remote["body"]) if remote is not None else None,
                       "expected_bytes": expected_bytes, "local_bytes": len(local_body) if local_body is not None else None,
                       "remote_bytes": len(remote["body"]) if remote is not None else None,
                       "status": "PASS" if local_valid and remote_valid else "FAIL"})
    index_manifest_matches = (index_bytes is not None and isinstance(runtime_data, dict)
                              and sha256(index_bytes) == runtime_data.get("manifestSha256"))
    chunks_match = (index_error is None and index_manifest_matches and len(chunks) == EXPECTED_DATA_CHUNKS
                    and len(asset_by_path) == EXPECTED_DATA_CHUNKS
                    and set(refs) == set(asset_by_path) and all(row["status"] == "PASS" for row in chunks))
    checks.append(check("all_297_indexed_data_chunks_match_site_and_public_http",
                        {"chunks": EXPECTED_DATA_CHUNKS, "data_index_sha256": runtime_data.get("manifestSha256") if isinstance(runtime_data, dict) else None},
                        {"chunks": len(chunks), "asset_manifest_entries": len(asset_by_path),
                         "data_index_sha256": sha256(index_bytes) if index_bytes is not None else None,
                         "app_manifest_sha256": runtime_data.get("manifestSha256") if isinstance(runtime_data, dict) else None,
                         "data_index_hash_matches_app_manifest": index_manifest_matches,
                         "index_error": index_error, "passed": sum(row["status"] == "PASS" for row in chunks)}, chunks_match))
    (out / "data-chunk-responses.json").write_text(json.dumps(chunks, indent=2), encoding="utf-8")

    # Verify all nine indexable pages, structured metadata, and CSP script hashes.
    sitemap_response = fetched.get("/sitemap.xml")
    sitemap = sitemap_response["body"] if sitemap_response else b""
    sitemap_error = None
    urls: list[str] = []
    try:
        urls = sitemap_urls(sitemap)
    except ET.ParseError as exc:
        sitemap_error = f"{type(exc).__name__}: {exc}"
    unique_urls = sorted(set(urls))
    sitemap_origin_ok = all(urlsplit(url).scheme == "https" and urlsplit(url).netloc == urlsplit(origin).netloc
                            and not urlsplit(url).query and not urlsplit(url).fragment for url in urls)
    checks.append(check("public_sitemap_has_nine_apex_indexable_pages",
                        {"count": EXPECTED_INDEXABLE_PAGES, "origin": origin},
                        {"count": len(urls), "unique_count": len(unique_urls), "urls": urls,
                         "all_https_apex": sitemap_origin_ok, "error": sitemap_error},
                        sitemap_error is None and len(urls) == EXPECTED_INDEXABLE_PAGES and len(unique_urls) == EXPECTED_INDEXABLE_PAGES and sitemap_origin_ok))
    page_rows = []
    for page_url in unique_urls:
        parsed = urlsplit(page_url)
        path = parsed.path or "/"
        route = path
        result = fetched.get(route)
        row: dict[str, Any] = {"url": page_url, "route": route, "status": "FAIL"}
        if result is None or result["status"] != 200:
            row["actual"] = "No successful receipt-mapped public response"
            page_rows.append(row)
            continue
        parser = PageFactsParser()
        try:
            parser.feed(result["body"].decode("utf-8"))
            jsonld = [json.loads(script["text"]) for script in parser.inline_scripts if script["type"] == "application/ld+json"]
            webpage_urls = [url for block in jsonld for url in find_webpage_urls(block)]
            response_csps = [value for key, value in result["record"].get("header_pairs", [])
                             if key.lower() == "content-security-policy"]
            tokens = inline_csp_tokens(parser)
            bad_tokens = [{"token": token, "missing_from_policies": [index for index, policy in enumerate(response_csps)
                                                                        if token not in policy]}
                          for token in tokens if any(token not in policy for policy in response_csps)]
            row.update({"canonical_values": parser.canonicals, "jsonld_blocks": len(jsonld),
                        "jsonld_webpage_urls": webpage_urls, "inline_script_csp_hashes": tokens,
                        "csp_policies": response_csps, "csp_missing_hashes": bad_tokens,
                        "http_csp_present": bool(response_csps)})
            row_pass = (parser.canonicals == [page_url] and bool(jsonld) and page_url in webpage_urls
                        and bool(response_csps) and not bad_tokens)
            row["status"] = "PASS" if row_pass else "FAIL"
        except (UnicodeDecodeError, ValueError, TypeError) as exc:
            row["actual"] = f"{type(exc).__name__}: {exc}"
        page_rows.append(row)
    checks.append(check("nine_page_canonicals_jsonld_and_inline_csp_hashes",
                        {"page_count": EXPECTED_INDEXABLE_PAGES, "each": "one exact canonical, parseable WebPage JSON-LD, all inline script hashes in effective CSP"},
                        {"page_count": len(page_rows), "passed": sum(row["status"] == "PASS" for row in page_rows),
                         "failed": sum(row["status"] == "FAIL" for row in page_rows)},
                        len(page_rows) == EXPECTED_INDEXABLE_PAGES and all(row["status"] == "PASS" for row in page_rows)))
    (out / "indexable-page-responses.json").write_text(json.dumps(page_rows, indent=2), encoding="utf-8")

    robots_response = fetched.get("/robots.txt")
    robots_text = robots_response["body"].decode("utf-8", errors="replace") if robots_response else ""
    runtime_response = fetched.get("/run/")
    runtime_parser = PageFactsParser()
    if runtime_response and runtime_response["status"] == 200:
        runtime_parser.feed(runtime_response["body"].decode("utf-8", errors="replace"))
    runtime_header = runtime_response["headers"].get("x-robots-tag", "") if runtime_response else ""
    runtime_csp_policies = ([value for key, value in runtime_response["record"].get("header_pairs", [])
                             if key.lower() == "content-security-policy"] if runtime_response else [])
    runtime_csp_tokens = inline_csp_tokens(runtime_parser)
    runtime_csp_missing = [{"token": token, "missing_from_policies": [index for index, policy in enumerate(runtime_csp_policies)
                                                                          if token not in policy]}
                           for token in runtime_csp_tokens
                           if any(token not in policy for policy in runtime_csp_policies)]
    runtime_csp_ok = bool(runtime_csp_policies) and not runtime_csp_missing
    checks.append(check("runtime_inline_scripts_covered_by_effective_http_csp",
                        {"inline_script_hashes": runtime_csp_tokens, "all_policies_cover_them": True},
                        {"csp_policies": runtime_csp_policies, "missing_hashes": runtime_csp_missing}, runtime_csp_ok))
    robots_allows_run = (bool(re.search(r"(?im)^\s*Allow\s*:\s*/\s*$", robots_text))
                         and not re.search(r"(?im)^\s*Disallow\s*:\s*/run(?:/|\s|$)", robots_text))
    noindex = any("noindex" in item.lower() for item in runtime_parser.robots) and "noindex" in runtime_header.lower()
    checks.append(check("runtime_preview_noindex_and_robots_allow_crawl",
                        {"runtime_meta_noindex": True, "runtime_header_noindex": True, "robots_allow_root": True, "robots_disallow_run": False},
                        {"runtime_robots_meta": runtime_parser.robots, "x_robots_tag": runtime_header,
                         "robots_allow_root": bool(re.search(r"(?im)^\s*Allow\s*:\s*/\s*$", robots_text)),
                         "robots_disallow_run": bool(re.search(r"(?im)^\s*Disallow\s*:\s*/run(?:/|\s|$)", robots_text))},
                        noindex and robots_allows_run))

    # Test each exact, active _redirects rule and explicit query preservation.
    redirects_text = files.get("_redirects", b"").decode("utf-8", errors="replace")
    redirect_checks = []
    for line_number, line in enumerate(redirects_text.splitlines(), 1):
        parts = line.split()
        if not parts or parts[0].startswith("#") or len(parts) < 3 or "*" in parts[0] or ":splat" in parts[1]:
            continue
        source, destination = parts[:2]
        try:
            status = int(parts[2])
        except ValueError:
            continue
        redirect_checks.append(verify_redirect(client, source, destination, status, f"redirect-rule-{line_number}"))
    # A literal query token makes preservation visible without requiring a browser.
    redirect_checks.append(verify_redirect(client, "/about", "/about/", 301, "about-query-preserved", "acceptance20261030"))
    www_origin = "https://www." + urlsplit(origin).netloc.removeprefix("www.")
    www_result = client.get(www_origin + "/about?acceptance20261030", "www-alias-query")
    www_location = www_result["headers"].get("location", "")
    www_expected_path = "/about"
    _, www_host, www_path = normalize_location(www_location, www_origin + "/about?acceptance20261030") if www_location else ("", "", "")
    www_query = urlsplit(www_location).query if www_location else ""
    www_pass = (www_result["status"] in {301, 308} and www_host == urlsplit(origin).netloc
                and www_path == www_expected_path and www_query == "acceptance20261030")
    redirect_checks.append(check("www_alias_redirects_to_apex_preserving_path_and_query",
                                 {"status": "301 or 308", "host": urlsplit(origin).netloc, "path": www_expected_path, "query": "acceptance20261030"},
                                 {"status": www_result["status"], "location": www_location, "host": www_host,
                                  "path": www_path, "query": www_query}, www_pass))
    checks.extend(redirect_checks)
    checks.append(check("published_redirect_rules", {"tested": len(redirect_checks), "all_pass": True},
                        {"tested": len(redirect_checks), "passed": sum(row["status"] == "PASS" for row in redirect_checks),
                         "failed": sum(row["status"] == "FAIL" for row in redirect_checks)},
                        all(row["status"] == "PASS" for row in redirect_checks)))

    # The status must be a real 404 and body must be the receipt-bound 404 page.
    missing = client.get(origin + MISSING_PATH, "real-404-route")
    expected_404 = files.get("404.html", b"")
    checks.append(check("real_missing_route_returns_receipt_bound_404",
                        {"status": 404, "body_sha256": sha256(expected_404)},
                        {"status": missing["status"], "body_sha256": sha256(missing["body"]), "body_bytes": len(missing["body"])},
                        missing["status"] == 404 and bool(expected_404) and missing["body"] == expected_404))
    return checks, client.records


def write_report(out: Path, report: dict[str, Any]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    counts: dict[str, int] = {}
    for item in report.get("checks", []):
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    status = report.get("status", "FAIL")
    (out / "summary.txt").write_text(f"status={status}\nchecks={json.dumps(counts, sort_keys=True)}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="public HTTPS apex origin, for example https://mkgrid.co.technology")
    parser.add_argument("--site", required=True, help="exact downloaded CI site directory")
    parser.add_argument("--receipt", required=True, help="matching helioforge.build-receipt.v1 CI receipt JSON")
    parser.add_argument("--out", required=True, help="new, nonexistent evidence directory")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    out = Path(args.out).expanduser().resolve()
    base = urlsplit(args.base_url)
    report: dict[str, Any] = {"schema": "helioforge.published-release-verification.v1",
                              "observed_at": datetime.now(UTC).isoformat(),
                              "command": ["verify-published-release.py", "--base-url", args.base_url,
                                          "--site", args.site, "--receipt", args.receipt, "--out", args.out],
                              "scope": "Ordinary read-only HTTP GETs, exact decoded public bytes, receipt-bound CI site; not a global cache or scientific validation.",
                              "production_mutated": False, "provider_calls": False, "requests": [], "checks": []}
    if (base.scheme != "https" or not base.netloc or base.username or base.password or base.query or base.fragment
            or base.path not in {"", "/"}):
        parser.error("--base-url must be a clean public HTTPS origin")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if out.exists():
        parser.error("--out must name a new, nonexistent directory")
    site = Path(args.site).expanduser().resolve()
    receipt_path = Path(args.receipt).expanduser().resolve()
    try:
        out.relative_to(site)
    except ValueError:
        pass
    else:
        parser.error("--out must be outside the read-only --site directory")
    try:
        preflight, receipt, files = check_receipt(site, receipt_path)
        report["checks"].extend(preflight)
        report["release"] = {"site": str(site), "receipt": str(receipt_path),
                             "source_base_commit": receipt.get("source_base_commit"),
                             "working_tree_dirty": receipt.get("working_tree_dirty"),
                             "ci_run_id": receipt.get("ci_run_id"), "ci_attempt": receipt.get("ci_attempt"),
                             "runtime_sha256": receipt.get("runtime_sha256"), "receipt_file_count": len(receipt.get("files", []))}
        preflight_ok = all(row["status"] == "PASS" for row in preflight)
        request_records: list[dict[str, Any]] = []
        report["requests"] = request_records
        if preflight_ok:
            facts = json.loads(files["app.json"].decode("utf-8"))
            http_checks, requests = verify_release(args.base_url, site, files, facts, out, args.timeout, request_records)
            report["checks"].extend(http_checks)
            report["requests"] = requests
        else:
            report["http_status"] = "NOT_RUN: exact site/receipt binding failed; no public requests sent"
    except Blocked as exc:
        report["status"] = "BLOCKED"
        report["block_reason"] = str(exc)
        report["requests"] = exc.records
        report["http_status"] = "Stopped after ordinary HTTP access denial; no alternate fingerprint attempted."
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        report["execution_error"] = f"{type(exc).__name__}: {exc}"
    if report.get("status") != "BLOCKED":
        statuses = [row["status"] for row in report["checks"]]
        report["status"] = ("PASS" if statuses and all(status == "PASS" for status in statuses)
                            and "execution_error" not in report else "FAIL")
    try:
        write_report(out, report)
    except FileExistsError:
        parser.error("--out must name a new, nonexistent directory")
    counts = {status: sum(row["status"] == status for row in report["checks"]) for status in ("PASS", "FAIL")}
    print(json.dumps({"status": report["status"], "checks": counts, "requests": len(report["requests"]),
                      "runtime_sha256": report.get("release", {}).get("runtime_sha256"), "out": str(out)}, indent=2))
    return 0 if report["status"] == "PASS" else 2 if report["status"] == "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
