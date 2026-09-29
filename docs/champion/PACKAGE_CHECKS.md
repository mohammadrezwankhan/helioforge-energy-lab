# Package checks

The packager excludes virtual environments, node_modules, Git internals, caches, runtime/test databases, real .env files and font binaries. It retains `.env.example`, compiled browser assets, source and audit evidence. No matching common private-key/API-token patterns were found in the scanned text files. This limited pattern check is not a comprehensive secret or vulnerability audit.

`RELEASE_MANIFEST.json` records the exact included files and hashes (excluding itself). `scripts/verify-release.py` validates file hashes and the 36/24/36 catalogue contract without external access. ZIP CRC and manifest-versus-ZIP bytes are checked during packaging. Hashes do not establish publisher identity or independent assurance.

Python compilation and shell syntax checks passed; this is not a substitute for the blocked Ruff lint check or unexecuted Windows/macOS native launch tests. The delivered verification report explains the browser transport/storage adapters and all material unverified areas.
