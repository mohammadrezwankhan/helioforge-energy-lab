"""Regenerate the read-only synthetic snapshot from the actual numerical engines."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from helioforge.dashboard import dashboard  # noqa: E402

snapshot = dashboard("FR")
text = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
(ROOT / "examples/dashboard-snapshot.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False)+"\n")
(ROOT / "apps/web/src/snapshot.ts").write_text("namespace HF {\n  export const SNAPSHOT: Dashboard = "+text+";\n}\n")
print("Updated synthetic snapshot. Rebuild the TypeScript frontend next.")
