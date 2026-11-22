"""Controlled browser fault tests. No GitHub calls or real outcomes are used.
Run: python tests/browser_error_states.py [--screenshots OUTPUT_DIR]
Requires playwright and its Chromium browser; uses a temporary local HTTP server.
"""
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import argparse,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
 class H(SimpleHTTPRequestHandler):
  def log_message(self,*a):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(H,directory=str(ROOT)));Thread(target=server.serve_forever,daemon=True).start()
 good=json.loads((ROOT/'dashboard/research-results.json').read_text());cases=[('missing',404,''),('syntax',200,'{broken'),('null',200,'null'),('empty',200,'{}')]
 for name,edit in [('duplicate',lambda d:d['macro'].__setitem__(0,d['macro'][1])),('non-number',lambda d:d['macro'][0].__setitem__('AP','0.9')),('out-of-range',lambda d:d['macro'][0].__setitem__('Brier',2)),('missing-project',lambda d:d['per_project'].pop())]:
  d=json.loads(json.dumps(good));edit(d);cases.append((name,200,json.dumps(d)))
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   for view in ['index.html','research-v2.html']:
    for name,status,body in cases:
     page=browser.new_page(viewport={'width':1200,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     page.route('http://127.0.0.1:8000/**',lambda r:r.fulfill(status=503,json={'detail':'Controlled offline API'}))
     page.route('**/research-results.json',lambda r,request,st=status,b=body:r.fulfill(status=st,content_type='application/json',body=b))
     page.goto(f'http://127.0.0.1:{server.server_port}/dashboard/{view}');page.wait_for_function("document.getElementById('studyLoadState').getAttribute('role')==='alert'")
     selector='#studyRegime' if view=='index.html' else '#regime';macro='#studyMacro' if view=='index.html' else '#macro'
     assert page.locator(selector).is_disabled();assert page.locator(macro+' tr').count()==0;assert not errors,errors
     if args.screenshots and name=='syntax' and view=='index.html':args.screenshots.mkdir(parents=True,exist_ok=True);page.locator('#studyLoadState').scroll_into_view_if_needed();page.screenshot(path=str(args.screenshots/'stage5-malformed-error.png'))
     page.unroute('**/research-results.json');page.route('**/research-results.json',lambda r:r.fulfill(json=good));page.locator('#studyRetry').click();page.wait_for_function("document.getElementById('studyLoadState').textContent.includes('loaded')");assert not page.locator(selector).is_disabled();assert page.locator(macro+' tr').count()==3;assert not errors,errors;page.close()
   # Loading state is real UI timing, with a controlled held response.
   page=browser.new_page();held=[];page.route('http://127.0.0.1:8000/**',lambda r:r.fulfill(status=503,json={'detail':'Controlled offline API'}));page.route('**/research-results.json',lambda r:held.append(r));page.goto(f'http://127.0.0.1:{server.server_port}/dashboard/index.html',wait_until='domcontentloaded');page.wait_for_function("document.getElementById('studyRegime').disabled");assert page.locator('#studyRetry').is_disabled();page.wait_for_timeout(50);assert held;held[0].fulfill(json=good);page.wait_for_function("!document.getElementById('studyRegime').disabled");page.close()
   # A direct file open must give actionable guidance, not a blank table.
   page=browser.new_page();page.goto((ROOT/'dashboard/research-v2.html').as_uri());page.wait_for_function("document.getElementById('studyLoadState').textContent.includes('local HTTP server')");page.close();browser.close()
  print('PASS: 16 malformed/missing-data cases and 16 successful retries, loading state and direct-file guidance. Controlled API failures; no external calls.')
 finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
