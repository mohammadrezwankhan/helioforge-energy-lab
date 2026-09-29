@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  where py >nul 2>nul
  if errorlevel 1 (
    where python >nul 2>nul
    if errorlevel 1 goto python_missing
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 goto failure
)
.venv\Scripts\python.exe -c "import sys; sys.exit(0 if (3,11)<=sys.version_info[:2]<=(3,13) else 1)"
if errorlevel 1 (
  echo This virtual environment needs Python 3.11-3.13. Review START_HERE.md.
  goto failure
)
.venv\Scripts\python.exe launch.py --check >nul 2>nul
if errorlevel 1 (
  echo Installing pinned local-app dependencies. This initial setup requires internet access.
  .venv\Scripts\python.exe -m pip install -e apps/api
  if errorlevel 1 goto failure
)
.venv\Scripts\python.exe launch.py %*
if errorlevel 1 goto failure
exit /b 0
:python_missing
echo Python 3.11-3.13 is required. Install Python and enable its PATH option.
pause
exit /b 1
:failure
echo The app could not start. Review the message above and the START_HERE.md guide.
pause
exit /b 1
