# HelioForge Champion 0.3.0 — start here

## Run the full app

Extract the **entire ZIP** to a folder you can write to. Do not launch files from inside the compressed archive. Keep the `apps`, `scripts` and `data` folders together.

You need **Python 3.11–3.13**. The compiled interface is included; **Node.js is not required to use the app**. First-time installation downloads pinned Python dependencies. Ordinary local calculations do not require an API key or a paid service.

| Computer | Start command from the extracted folder |
|---|---|
| Windows | Double-click `start-windows.cmd` |
| macOS | Run `sh start-macos.command` in Terminal |
| Linux | Run `sh start-linux.sh` in a terminal |

The launcher opens **http://127.0.0.1:8000** after the server is ready. Leave its terminal open while using the app. Stop it with **Ctrl+C**. The standard launcher explicitly disables external AI, binds to this computer only, and does not deploy anything.

The launch process was tested on Linux with Python 3.13.5. Windows/macOS launcher scripts are provided but were not executed on those operating systems. Direct browser-to-localhost navigation was restricted in the build environment; the browser verification report explains the host transport adapter used instead.

### Manual setup / troubleshooting

```sh
python -m venv .venv
# Windows:
.venv\Scripts\python.exe -m pip install -e apps/api
.venv\Scripts\python.exe launch.py
# macOS / Linux instead:
.venv/bin/python -m pip install -e apps/api
.venv/bin/python launch.py
```

Use your supported interpreter's command (`python`, `python3`, or `py -3.13`) for the first line. If the existing `.venv` was created with an unsupported Python version, recreate that environment with Python 3.11–3.13; keep your `data` folder and exported work.

**Port already in use?** Close the other local instance, or run the virtual environment's Python with `launch.py --port 8001`. No existing process is killed automatically. Use `--no-browser` to open the printed address yourself. `launch.py --check` checks dependencies and packaged assets without starting the server. When changing ports, browser workspace shortcuts may differ; API history is still available from the same database.

**Installation failed?** Check Python version, network/proxy access for package downloads and write permission to the extracted folder. Read the actual error before trying again. Do not disable your security software or expose the API publicly to fix a local setup problem.

**Snapshot preview?** The Python server is not connected. Start the full app and use its printed address. Press the connection indicator to reconnect. A standalone HTML file does not execute the Python models.

## Explore immediately without installation

Open **`HelioForge-Preview.html`**. This is the self-contained interface with bundled, synthetic example results. You can explore the architecture atlas, 3D objects, methodology and lessons. **New numerical calculations and API-backed history are disabled.** File-browser policy and browser storage support vary; no file-launch compatibility certification is implied.

## Your first useful experiment

Open **Quick start → Open the reference case**. This loads the Hospital islanding microgrid with its reference scenario. Give the inputs a name using **Saved setups**, then run the energy screen and pin its result. Select **Four-hour outage**, run again, and pin the second result. In **Scenario compare**, inspect critical shortfall, load served, and initial/terminal battery energy—not cost alone. Export the comparison to retain the exact assumptions.

Use **Ctrl+K** (or **Cmd+K**) to search workspaces, architectures and lessons. Arrow keys select a command; Enter opens it; Escape closes the dialog. The 3D scene also has keyboard/camera controls and named asset buttons. Use the animation toggle or your system's reduced-motion preference.

## Where your work goes

**Saved setups:** up to 20 named hybrid configurations in browser storage. A saved setup is an input shortcut, not a solved result. Opening it requires a fresh calculation unless you separately reopen an existing run from history. Export individual setups to move them between computers; the existing Import control accepts those configuration files.

**Workspace recovery:** stores the last valid hybrid inputs and up to three pinned run references. The app retrieves saved numerical results from the actual local API before displaying them. A missing record is reported rather than invented. Damaged cache data is retained for recovery download until you explicitly confirm a reset. The workspace JSON export is an inspectable backup, not an automatically imported bundle of numerical results.

**Analysis history:** real calculations are stored in `data/helioforge.sqlite3` by the standard launcher. Hybrid runs can be reopened into the lab. Every run can be downloaded as JSON. The UI lists the latest 100; it does not delete older records. The database is a local research record, not a signed or tamper-evident ledger.

**Other-model drafts:** unsubmitted storage, PV, finance and related form edits survive navigation in the current tab. They are not promised to survive closing/reloading the tab. Passwords, external-processing mode and consent are deliberately excluded from draft retention. Completed results are preserved on same-market reconnection; switching market loads that market's illustrative defaults.

**Privacy:** the standard launch mode sends no external AI requests. Do not place sensitive data in a public preview, commit your database to a repository, or publish the local API. The app has no multi-user authentication layer. Browser shortcuts are local to the browser context; clearing browser data removes them, not API history. Prefer one editing tab to avoid last-writer overwrites between tabs.

## Backup and recovery

Stop the app before making a simple file copy of your database. Keep an independent copy of `data/helioforge.sqlite3`, plus exported configurations and comparisons. Do not replace an existing database while the server is running. For a deliberate restoration, keep the current database as a separate backup, place the chosen backup at the configured path, restart the app and check run IDs and results in history. A small synthetic SQLite backup/restore was rehearsed; this is not evidence for a large production restoration.

There is no schema migration in this update. To compare with the original v0.2 source, preserve the original archive and use a separate extracted folder/virtual environment. Never overwrite your only copy of historical research data.

## Boundaries worth keeping visible

36 architectures are included: **19 runnable hourly electricity screens and 17 study-only architectures**. There are 24 scenarios, 36 lessons and 285 applicable runnable architecture/scenario combinations. Advanced multi-carrier and dynamic-control pictures are not fully solved physics. Results use synthetic profiles and explicit assumptions. They are not plant-control commands, a hospital safety assessment, investment approval, accredited learning outcomes or live market forecasts.

Read `docs/champion/VERIFICATION.md` for actual test results and remaining checks. Read `docs/champion/RELEASE_PLAN.md` before considering any public or organizational deployment.
