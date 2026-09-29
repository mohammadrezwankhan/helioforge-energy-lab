"""Local process launch and synthetic database recovery checks. No production data."""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def passed(name):checks.append(name);print('PASS',name,flush=True)

def stop(process):
    if process.poll() is None:
        if os.name=='nt':process.terminate()
        else:process.send_signal(signal.SIGINT)
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill();process.wait();raise

with tempfile.TemporaryDirectory(prefix='helioforge-launch-check-') as folder:
    tmp=Path(folder)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    url=f'http://127.0.0.1:{port}';db=tmp/'original.sqlite3'
    env=os.environ.copy();env['HELIOFORGE_DB']=str(db);env['ENABLE_OPENAI']='true' # Launcher must deliberately override this.
    r=subprocess.run([sys.executable,'launch.py','--check'],cwd=ROOT,capture_output=True,text=True)
    assert r.returncode==0,r.stderr;passed('Packaged runtime preflight passes without installing or starting anything')
    procs=[]
    try:
        def start(database):
            env['HELIOFORGE_DB']=str(database)
            log=open(tmp/(database.stem+'-server.log'),'a')
            proc=subprocess.Popen([sys.executable,'launch.py','--port',str(port),'--no-browser'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            procs.append(proc)
            for _ in range(120):
                if proc.poll() is not None:raise RuntimeError((tmp/(database.stem+'-server.log')).read_text())
                try:
                    response=httpx.get(url+'/api/health',timeout=0.4)
                    if response.status_code==200:return proc,response.json()
                except httpx.HTTPError:pass
                time.sleep(0.1)
            raise RuntimeError('Local launcher did not become ready')
        process,health=start(db)
        assert health['version']=='0.3.0' and health['openai_enabled'] is False
        passed('Local launcher starts the packaged app on a custom loopback port with external AI disabled')
        with httpx.Client(base_url=url,timeout=40) as c:
            index=c.get('/');assert index.status_code==200 and 'HelioForge Champion' in index.text
            assert 'script-src' in index.headers['content-security-policy']
            assert c.get('/app.js').status_code==200
            assert c.get('/styles.css').status_code==200
            passed('Served HTML, compiled JavaScript and CSS are available with the declared CSP header')
            assert c.get('/api/health',headers={'host':'hostile.example'}).status_code==400
            r=c.post('/api/storage/optimize',json={},headers={'origin':url});assert r.status_code==200,r.text
            saved=c.get('/api/runs/'+r.json()['run_id']).json()
            passed('Custom-port origin works; unexpected hostname is rejected; real synthetic calculation is saved')
        collision=subprocess.run([sys.executable,'launch.py','--port',str(port),'--no-browser'],cwd=ROOT,env=env,capture_output=True,text=True)
        assert collision.returncode==2 and 'in use' in collision.stderr
        assert process.poll() is None
        passed('Occupied-port launch is rejected without stopping the already-running app')
        stop(process)
        process,health=start(db)
        assert httpx.get(url+'/api/runs/'+saved['run_id'],timeout=10).json()==saved
        passed('A saved calculation survives a real process stop and restart with identical inputs/results')
        stop(process)
        backup=tmp/'restored.sqlite3'
        with sqlite3.connect(db) as source,sqlite3.connect(backup) as target:
            source.backup(target)
            assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        process,health=start(backup)
        assert httpx.get(url+'/api/runs/'+saved['run_id'],timeout=10).json()==saved
        passed('Synthetic SQLite backup/restore rehearsal passes integrity check and restores the exact saved run')
        stop(process)
        if os.name!='nt':assert process.returncode==0;passed('Ctrl+C stops the local launcher and child server cleanly on the tested Linux environment')
    finally:
        for process in procs:stop(process)
report={'checks_passed':len(checks),'checks':checks,'platform':sys.platform,'python':sys.version,'limitations':'Small synthetic database only. Windows/macOS scripts and automatic browser opening not executed.'}
out=ROOT/'docs/champion/launcher-validation.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(checks)} local launcher/recovery checks passed.')
