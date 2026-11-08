"""Import only hash-verified blobs; never create commits, refs, or execute payloads."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parent
REPOSITORY = "mohammadrezwankhan/helioforge-energy-lab"
BRANCH = "transfer/helio-maintenance-20261108"
PARENT = "74269ecb6abe738aa8ea6916d93e1d9efd62c1b6"
TREE = "ce5c50e63e6bf8d0d4e71fe72dc2a9543fec6d2c"
PACK_SHA256 = "d78707e1b17804f01bb1dc410943158a392083d06f6666ebe7a899431b54e788"


def git(*args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], input=data, capture_output=True, check=True
    ).stdout


def main() -> None:
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != f"refs/heads/{BRANCH}"
        or os.environ.get("GITHUB_EVENT_NAME") != "push"
    ):
        raise SystemExit("This transfer is restricted to its exact trusted push branch.")

    manifest = json.loads((ROOT / "manifest.json").read_text())
    if (
        manifest["repository"] != REPOSITORY
        or manifest["parent"] != PARENT
        or manifest["tree"] != TREE
        or manifest["pack_sha256"] != PACK_SHA256
        or len(manifest["files"]) != 8
    ):
        raise SystemExit("Transfer manifest does not match the reviewed candidate.")

    pack = base64.b64decode((ROOT / "objects.pack.b64").read_text().strip(), validate=True)
    if hashlib.sha256(pack).hexdigest() != PACK_SHA256:
        raise SystemExit("Transfer pack digest mismatch.")
    git("fetch", "--no-tags", "--depth=1", "origin", PARENT)
    if git("rev-parse", f"{PARENT}^{{tree}}").decode().strip() != manifest["base_tree"]:
        raise SystemExit("Base tree does not match the reviewed parent.")
    git("index-pack", "--stdin", "--fix-thin", data=pack)
    if git("cat-file", "-t", TREE).decode().strip() != "tree":
        raise SystemExit("Candidate tree is missing.")

    expected_paths = sorted(entry["path"] for entry in manifest["files"])
    changed_paths = sorted(git("diff", "--name-only", PARENT, TREE).decode().splitlines())
    if changed_paths != expected_paths:
        raise SystemExit("Candidate contains an unexpected changed path.")

    # Verify every complete blob before allowing any remote write.
    blobs = []
    for entry in manifest["files"]:
        metadata = git("ls-tree", TREE, "--", entry["path"]).decode().strip()
        if metadata != f'{entry["mode"]} blob {entry["sha"]}\t{entry["path"]}':
            raise SystemExit(f'Tree entry mismatch: {entry["path"]}')
        content = git("cat-file", "blob", entry["sha"])
        digest = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        if len(content) != entry["bytes"] or digest != entry["sha"]:
            raise SystemExit(f'Blob verification failed: {entry["path"]}')
        blobs.append((entry, content))

    token = os.environ["GITHUB_TOKEN"]
    for entry, content in blobs:
        payload = json.dumps({
            "encoding": "base64",
            "content": base64.b64encode(content).decode(),
        }).encode()
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPOSITORY}/git/blobs",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
        if result.get("sha") != entry["sha"]:
            raise SystemExit(f'Remote blob digest mismatch: {entry["path"]}')
        print(f'Verified blob {entry["sha"]} {entry["path"]}', flush=True)

    print(f"Uploaded {len(blobs)} verified blobs for tree {TREE}; no refs changed.")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a") as out:
            out.write(f"Verified {len(blobs)} blobs for `{TREE}` based on `{PARENT}`.\n")
            out.write("This job created no commits or refs and executed no transferred code.\n")


if __name__ == "__main__":
    main()
