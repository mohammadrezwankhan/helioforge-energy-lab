# Execution capability inventory

| Capability | Observed availability and use |
|---|---|
| Repository read/write | Available. Clean baseline `74d6730e38323b69c180d7f4b4945d11010203f3` copied into a Git worktree on `repair/appraisal-20261028`. Original checkout preserved. App-managed worktree registration was unavailable for this source location; ordinary Git worktree used. |
| Shell/filesystem | Windows 11, PowerShell, Node 24.22.1, Python 3.12.14 from the existing audit venv. No new runtime application dependency. `npm ci --ignore-scripts` installed locked development dependencies. |
| Browser automation | Playwright Chromium, Firefox and WebKit available on Windows. Isolated contexts, pointer/keyboard/touch emulation, screenshots, trace, downloads, viewport/network/CPU emulation used. Browser versions are recorded in reports. No personal profile was claimed. |
| Native subagents | Available and explicitly requested. Three pinned worker roles plus a pinned read-only reviewer, disjoint write scopes, no parent history; at most four concurrent agents. No close-agent tool exposed; completed agents idle. |
| Network | Permitted-browser production retrieval succeeded. Direct scripted urllib received Cloudflare 1010/403; preserved as a failed retrieval, not an outage. GitHub read-only CI logs and Cloudflare read-only deployment metadata accessible. |
| Deployment | Existing deployment IDs and status read through authorized Cloudflare connector. No write capability was probed, no candidate pushed/published, no production settings changed. |
| Real devices | No physical phone/tablet/macOS device available for this task. Desktop engines and CSS/input emulation are labeled accordingly. |
| Assistive technology | No NVDA process or installation found in the inspected standard locations; no native VoiceOver/TalkBack session available. Automated keyboard/axe checks do not replace AT. |
| Accounts/providers | Existing GitHub and Cloudflare read access used. No provider credentials inspected, no paid or external model calls invoked, no hardware connected. No account/profile capability inferred from presence of a connector. |
| Local API/state | Fresh temporary SQLite fixtures and isolated browser storage. No user production database or saved browser workspace used. A first SQLite location failed with a disk-I/O error; a new temporary fixture path worked. |
| Host filtering | AdGuard modified local HTTP HTML and CSP. Final exact-byte static testing uses an isolated HTTPS loopback fixture with a temporary self-signed certificate. No host protection or certificate-store settings changed. |
| Physical/field/performance telemetry | Real-device and field evidence absent. No analytics added. Desktop lab raw metrics retained, including invalid harness observations. |

Primary appraisal: all 41 pages read from `HelioForge_Critical_Appraisal (2).pdf`, SHA-256 `2f6c73a8f23b33a2521e539bc279a8641775d6f73779b9aff6595311af54753b`. Companion ZIP `HelioForge_Audit_Package.zip`, SHA-256 `35019b71a284d1f22d9ddd9d6040fca7cab61eba796f35d640b9c18e7e21f145`. Original CSV plans are preserved in `source-plan/` and never relabeled as executions.

Repository instructions, README, methodology, security and validation documentation were read. The systematic-debugging and PDF-reading skills were used. No safety setting, global protection, hosted access rule or CSP was weakened to pass a test.
