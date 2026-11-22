#!/usr/bin/env bash
# Check release bytes in a fixed Linux/amd64 Python environment.
set -euo pipefail
image='python:3.13.18-slim-bookworm@sha256:f3dac913ab53b78c64f26d5518fcd7043d5a1a46522d6a493b598c3ed12f62a6'
git archive HEAD | docker run --rm -i --platform linux/amd64 --workdir /work "$image" sh -eu -c '
  tar -xf -
  python -m pip install --disable-pip-version-check --only-binary=:all: --require-hashes -r scripts/hybrid-publication-requirements.txt
  sha256sum examples/hybrid-bundle.json examples/hybrid-catalog.json examples/hybrid-default.json examples/hybrid-matrix.json apps/web/src/hybrid-data.ts > /tmp/committed
  python scripts/generate-hybrid-assets.py
  sha256sum -c /tmp/committed
'
