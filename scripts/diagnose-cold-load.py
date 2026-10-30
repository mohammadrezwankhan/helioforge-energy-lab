"""Supplemental cold-load trace. Tracing adds overhead; this is not the budget run."""
import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', required=True)
parser.add_argument('--runtime', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expected = hashlib.sha256(args.runtime.read_bytes()).hexdigest()
report = {'schema': 'helioforge.cold-load-diagnostic.v1', 'started_at': datetime.now(timezone.utc).isoformat(),
          'url': args.url, 'runtime_sha256': expected, 'platform': platform.platform(),
          'physical_device': False, 'tracing_overhead': True, 'cpu_rate': 4,
          'network': {'latency_ms': 150, 'download_mbps': 1.6, 'upload_mbps': 0.75}}
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    report['browser_version'] = browser.version
    context = browser.new_context(viewport={'width': 390, 'height': 844},
                                  ignore_https_errors=args.url.startswith('https://127.0.0.1:'))
    context.add_init_script("""window.coldAudit={lcp:[],longTasks:[],cls:0};
      for(const type of ['largest-contentful-paint','longtask','layout-shift'])
        new PerformanceObserver(list=>{for(const e of list.getEntries()){
          if(type==='largest-contentful-paint')coldAudit.lcp.push({time:e.startTime,size:e.size,
            element:e.element?.tagName,id:e.element?.id,className:e.element?.className,text:e.element?.textContent?.slice(0,300)});
          if(type==='longtask')coldAudit.longTasks.push({start:e.startTime,duration:e.duration});
          if(type==='layout-shift'&&!e.hadRecentInput)coldAudit.cls+=e.value;
        }}).observe({type,buffered:true});""")
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    cdp = context.new_cdp_session(page)
    cdp.send('Network.enable')
    cdp.send('Network.clearBrowserCache')
    cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
    cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 150,
             'downloadThroughput': 1_600_000 / 8, 'uploadThroughput': 750_000 / 8})
    completion = {}
    cdp.on('Tracing.tracingComplete', lambda event: completion.update(event))
    cdp.send('Profiler.enable')
    cdp.send('Profiler.start')
    cdp.send('Tracing.start', {'categories': 'devtools.timeline,v8,blink.user_timing,disabled-by-default-devtools.timeline.stack',
                             'transferMode': 'ReturnAsStream'})
    response = page.goto(args.url + '#hybrid', wait_until='load', timeout=120000)
    page.locator('#main-content h1').wait_for()
    page.wait_for_timeout(1800)
    report['navigation_status'] = response.status
    report['response_sha256'] = hashlib.sha256(response.body()).hexdigest()
    report['artifact_match'] = report['response_sha256'] == expected
    report['metrics'] = page.evaluate("""()=>({...coldAudit,
      navigation:performance.getEntriesByType('navigation').map(e=>e.toJSON()),
      resources:performance.getEntriesByType('resource').map(e=>e.toJSON()),
      paints:performance.getEntriesByType('paint').map(e=>e.toJSON()),
      dom_nodes:document.querySelectorAll('*').length})""")
    report['errors'] = errors
    profile = cdp.send('Profiler.stop')['profile']
    (args.output / 'cpu-profile.json').write_text(json.dumps(profile), encoding='utf-8')
    cdp.send('Tracing.end')
    deadline = time.monotonic() + 60
    while not completion and time.monotonic() < deadline:
        page.wait_for_timeout(25)
    if not completion.get('stream'):
        raise RuntimeError('Trace stream unavailable')
    raw = []
    while True:
        chunk = cdp.send('IO.read', {'handle': completion['stream']})
        raw.append(chunk['data'])
        if chunk.get('eof'):
            break
    cdp.send('IO.close', {'handle': completion['stream']})
    (args.output / 'trace.json').write_text(''.join(raw), encoding='utf-8')
    report['trace_data_loss'] = completion.get('dataLossOccurred', False)
    page.screenshot(path=str(args.output / 'viewport.png'))
    browser.close()
report['finished_at'] = datetime.now(timezone.utc).isoformat()
(args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'artifact_match': report['artifact_match'], 'lcp': report['metrics']['lcp'],
                  'long_tasks': report['metrics']['longTasks'], 'errors': errors}))
