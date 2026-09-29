#!/usr/bin/env sh
set -eu
cd "$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Python 3.11-3.13 is required.' >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -c 'import sys; sys.exit(0 if (3,11)<=sys.version_info[:2]<=(3,13) else 1)' || { printf '%s\n' 'This environment requires Python 3.11-3.13. See START_HERE.md.' >&2; exit 1; }
if ! .venv/bin/python launch.py --check >/dev/null 2>&1; then
  printf '%s\n' 'Installing pinned local-app dependencies. Initial setup requires internet access.'
  .venv/bin/python -m pip install -e apps/api
fi
exec .venv/bin/python launch.py "$@"
