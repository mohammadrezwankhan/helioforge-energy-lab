#!/usr/bin/env bash
# Prove that the hybrid generator is byte-deterministic on this runner.
# Run from a clean Git checkout; the scratch worktree isolates generated writes.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
scratch="$(mktemp -d)"
cleanup() {
  cd "$root"
  git worktree remove --force "$scratch/work" >/dev/null 2>&1 || true
  rm -rf "$scratch"
}
trap cleanup EXIT

git -C "$root" worktree add --detach "$scratch/work" HEAD
cd "$scratch/work"

artifacts=(
  examples/hybrid-bundle.json
  examples/hybrid-catalog.json
  examples/hybrid-default.json
  examples/hybrid-matrix.json
  apps/web/src/hybrid-data.ts
)

python scripts/generate-hybrid-assets.py
sha256sum "${artifacts[@]}" > "$scratch/first.sha256"
python scripts/generate-hybrid-assets.py
sha256sum "${artifacts[@]}" > "$scratch/second.sha256"

diff -u "$scratch/first.sha256" "$scratch/second.sha256"
printf 'PASS: two same-runner generations produced byte-identical assets.\n'
printf 'NOTE: this does not assert cross-platform equality to the committed frozen bytes.\n'
