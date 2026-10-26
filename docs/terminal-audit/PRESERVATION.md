# Source preservation proof

Baseline: d14b71f50ef400a50d3ccd4792dcd59238c64f56. Independent explorer reviewed the current diff and inventory; no original route or handler was lost.

| Contract | Preserved |
|---|---:|
| Client routes | 12/12 |
| API method/path/handler tuples | 30/30 |
| Original event-hook registrations | 49/49 |
| Original data attribute identities | 67/67 |
| Selector/dataset identities | 128/128 |
| Studies | 59/59 |
| Architectures (runnable/study-only) | 36 (19/17) |
| Scenarios / lessons | 24 / 36 |

`main.py`, `schemas.py`, eleven original engine modules and the hybrid catalogue match baseline after CRLF normalization. The new terminal.py model is isolated. __init__.py and package versions intentionally change to2.0.0; API health wire version remains0.3.0 for compatibility. New controller installation and compare composition retain the original paths. Baseline export inventory has27 matches plus three associations explicitly supplemented in AUDIT_MANIFEST.md.

This source proof is supplemented by unit and browser evidence in VERIFICATION.md. It does not claim every possible input/interaction was exhaustively tested. Numerical boundaries are tested rather than inferred from a screenshot.
