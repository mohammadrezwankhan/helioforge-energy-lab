#!/usr/bin/env python3
"""Launch the packaged, single-user local app without a Node.js runtime.

Does not install packages, expose the server on a network interface, or enable
external AI. Setup scripts perform the explicit one-time dependency installation.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent
REQUIRED = {'fastapi':'0.142.0','starlette':'1.3.1','uvicorn':'0.48.0','pydantic':'2.13.4','numpy':'2.3.5','scipy':'1.17.0'}

def check() -> list[str]:
    problems=[]
    if not (3,11) <= sys.version_info[:2] <= (3,13):
        problems.append('Use Python 3.11, 3.12 or 3.13 for this packaged environment.')
    for name, version in REQUIRED.items():
        try:
            actual=importlib.metadata.version(name)
            if actual!=version:problems.append(f'{name}: expected {version}; found {actual}. Use the project virtual environment.')
        except importlib.metadata.PackageNotFoundError:
            problems.append(f'{name} is not installed.')
    for path in ['apps/web/dist/index.html','apps/web/dist/app.js','apps/web/dist/styles.css','apps/api/helioforge/main.py']:
        if not (ROOT/path).is_file():problems.append(f'Missing packaged file: {path}. Extract the complete ZIP first.')
    return problems

def main() -> int:
    parser=argparse.ArgumentParser(description='Run HelioForge Champion on this computer only.')
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--check',action='store_true',help='Check the environment without starting the server.')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Choose a port from 1024 to 65535.')
    problems=check()
    if problems:
        print('Setup needs attention:\n'+'\n'.join('  - '+p for p in problems),file=sys.stderr)
        print('Run start-windows.cmd or start-macos.command / start-linux.sh, or install apps/api into a virtual environment.',file=sys.stderr)
        return 1
    if args.check:
        print('PASS: Python, pinned runtime dependencies and packaged frontend are available. External AI remains disabled.')
        return 0
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:sock.bind(('127.0.0.1',args.port))
    except OSError:
        print(f'Port {args.port} is in use. Close the existing app or use --port {args.port+1 if args.port<65535 else 8000}. No process was stopped.',file=sys.stderr)
        return 2
    env=os.environ.copy()
    env['PYTHONPATH']=str(ROOT/'apps/api')+os.pathsep+env.get('PYTHONPATH','')
    db=Path(env.get('HELIOFORGE_DB',str(ROOT/'data/helioforge.sqlite3'))).expanduser().resolve()
    try:db.parent.mkdir(parents=True,exist_ok=True)
    except OSError as exc:
        print(f'Cannot create the local data folder: {exc}',file=sys.stderr);return 1
    env['HELIOFORGE_DB']=str(db)
    env['ALLOWED_HOSTS']='127.0.0.1,localhost,[::1]'
    env['ALLOWED_ORIGINS']=f'http://127.0.0.1:{args.port},http://localhost:{args.port}'
    env['ENABLE_OPENAI']='false'
    url=f'http://127.0.0.1:{args.port}'
    print(f'HelioForge Champion 0.3.0\nLocal app: {url}\nLocal data: {db}\nExternal AI: disabled\nPress Ctrl+C to stop.',flush=True)
    child=subprocess.Popen([sys.executable,'-m','uvicorn','helioforge.main:app','--host','127.0.0.1','--port',str(args.port)],cwd=ROOT,env=env)
    def open_when_ready() -> None:
        for _ in range(100):
            if child.poll() is not None:return
            try:
                with urlopen(url+'/api/health',timeout=0.5) as response:
                    health=json.load(response)
                if health.get('version')=='0.3.0':
                    if not webbrowser.open(url):print(f'Open {url} in your browser.',flush=True)
                    return
            except (URLError,OSError,ValueError):pass
            time.sleep(0.15)
        print(f'Automatic browser opening was not completed. Check the server output and open {url} manually.',flush=True)
    if not args.no_browser:threading.Thread(target=open_when_ready,daemon=True).start()
    try:return child.wait()
    except KeyboardInterrupt:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        print('\nHelioForge stopped. Saved runs remain in the local database.')
        return 0

if __name__=='__main__':raise SystemExit(main())
