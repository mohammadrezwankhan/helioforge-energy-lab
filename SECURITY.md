## Champion 0.3 local boundary

`launch.py` binds only to `127.0.0.1`, explicitly disables external AI, and sets matching local Host/Origin allow-lists for the chosen port. Unexpected Host headers are rejected. API responses use `Cache-Control: no-store`. These are defense-in-depth controls, **not authentication**. A local client with access can still read or modify local research records. Do not publish this app as a multi-user service without a separately reviewed authentication, authorization, TLS, retention and deployment design.

The existing optional external adapter is preserved for explicit developer configuration but was not exercised with a real provider in this build. No keys are included. See `docs/champion/VERIFICATION.md` for tested and untested boundaries.

---

# Security and deployment boundaries

Version 0.1 is for a trusted user on their own machine. Bind to `127.0.0.1`. **Do not expose it to the Internet or an untrusted LAN as shipped.** Ordinary model and pilot endpoints do not implement user authentication, authorization or tenancy.

Implemented defences include strict bounded request schemas, a 1 MB request-body limit, parameterized SQLite statements, HTML escaping, safe source URLs, spreadsheet-formula-safe text CSV exports, browser-origin checks for writes, limited CORS, security headers and an explicit key/consent gate for potentially billable AI calls. CORS and origin checks are not authentication. Same-origin XSS, compromised local software, DNS rebinding/Host policies, denial of service and an attacker with filesystem access require broader controls.

The source has no trading, SCADA, BMS or inverter control connector. Pilot state changes do not authorize fieldwork. Treat an AI result as untrusted research text, never an operational command.

Keep API keys in environment/secrets management. Never commit `.env`, `data/`, `.sqlite3` files, client inputs, audit logs or model prompts containing confidential information. SDK tracing is disabled, but opt-in external execution still transmits the brief and evidence to the configured provider. Configure actual provider spending limits.

SQLite is not encrypted or tamper-evident here. Make local backups and apply device access controls. Retention, per-user deletion, key rotation and managed secret storage are operator responsibilities until a production design exists.

## Reporting

Do not post credentials, personal data or exploitable private details in a public issue. Before public deployment, the repository owner must enable GitHub private vulnerability reporting or publish a monitored private security contact. That channel is **not configured by this local deliverable**. For local-only use, stop the server and contact the repository owner through an already trusted private channel.

No penetration test, formal security certification, dependency vulnerability clearance or production sign-off is claimed. See docs/VALIDATION.md for checks actually performed.
