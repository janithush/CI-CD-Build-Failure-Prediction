"""Combined application acceptance. Default: actual local model replays + clearly
controlled live/legacy UI responses, with no external calls. Optional real public
preview is read-only and requires explicit --live-public-repository/--workflow-id.
Set BUILDRISK_PUBLIC_READ_TOKEN only in the server environment when authorized.
"""
from pathlib import Path
from threading import Thread
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
import subprocess,sys,os,time,json,urllib.request,tempfile,argparse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);parser.add_argument('--live-public-repository');parser.add_argument('--workflow-id',type=str);args=parser.parse_args()
 if args.live_public_repository and not args.workflow_id:parser.error('--workflow-id is required for an explicit live preview')
 out=args.screenshots or Path(tempfile.mkdtemp(prefix='combined-browser-evidence-'));out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as temp:
  env=dict(os.environ,PYTHONPATH=os.environ.get('PYTHONPATH','')+os.pathsep+str(ROOT),BUILDRISK_DATABASE_PATH=str(Path(temp)/'history.sqlite3'))
  class H(SimpleHTTPRequestHandler):
   def log_message(self,*a):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(H,directory=str(ROOT)));Thread(target=server.serve_forever,daemon=True).start()
  log=open(out/'acceptance-api.log','w');api=subprocess.Popen([sys.executable,'-m','uvicorn','api.main:app','--host','127.0.0.1','--port','8000'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   for _ in range(60):
    try:urllib.request.urlopen('http://127.0.0.1:8000/health');break
    except Exception:time.sleep(.2)
   else:raise RuntimeError('Local API did not start. Check the bounded test log.')
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write']);page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));url=f'http://127.0.0.1:{server.server_port}/dashboard/index.html';page.goto(url);page.wait_for_function("document.querySelectorAll('#studyMacro tr').length===3")
    # Native keyboard-capable quick-picks, visibility, blank-copy and controlled connect.
    for chip in page.locator('.repo-chip').all():chip.click();assert 'github.com/' in page.locator('#github_repo_url').input_value()
    page.locator('#copyShaBtn').click();assert page.locator('#toastContainer').inner_text()
    page.locator('#github_token').fill('controlled-not-a-real-credential');page.locator('#toggleTokenBtn').click();assert page.locator('#github_token').get_attribute('type')=='text';page.locator('#toggleTokenBtn').click()
    connection=json.loads((ROOT/'tests/fixtures/combined/public-repository-connection.json').read_text());page.route('**/connect-github-repo',lambda r:r.fulfill(json=connection));page.locator('#connectBtn').click();page.wait_for_function("!document.getElementById('predictBtn').disabled")
    page.locator('#copyShaBtn').click();assert page.evaluate('navigator.clipboard.readText()')==connection['commit_analysis']['commit_id']
    page.locator('#predictBtn').click();page.wait_for_function("document.getElementById('toastContainer').textContent.includes('Prediction disabled')");assert page.locator('#feedbackBtn').is_disabled()
    # A deliberate low-model/high-advice UI fixture. This is not provider or scientific evidence.
    advice={'prediction':{'raw_model_probability':2.0,'ml_failure_probability':2.0,'advisory_risk_score':80.0,'final_failure_risk_score':80.0,'risk_level':'Review','prediction':'Controlled advice display test','decision_threshold':41.5,'reasons':['Controlled fixture: raw probability remains below cutoff'],'suggestions':['Controlled test only'],'risky_files':[]}}
    page.route('**/predict-connected-repo',lambda r:r.fulfill(json=advice));page.locator('#predictBtn').click();page.wait_for_function("document.getElementById('riskScore').textContent==='80.0/100'");assert page.locator('#mlScore').inner_text()=='2.0%';assert page.locator('#feedbackBtn').is_disabled()
    history={'history':[{'timestamp':str(i),'source':'controlled-fixture','risk_score':i,'risk_level':'Review'} for i in range(12)]};page.route('http://127.0.0.1:8000/history?*',lambda r:r.fulfill(json=history));page.locator('button[onclick="loadHistory()"]').first.click();page.wait_for_function("document.getElementById('historyPageText').textContent.includes('of 3')");page.locator('button[onclick="nextHistoryPage()"]').click();assert 'Page 2' in page.locator('#historyPageText').inner_text();page.locator('button[onclick="previousHistoryPage()"]').click();page.locator('button[title="Reload history from SQLite"]').click()
    assert 'controlled-not-a-real-credential' not in json.dumps(page.evaluate('({...localStorage})'))
    # All nine research regime/model choices use actual fitted-model local replay.
    records=[]
    for regime in ['original5-zero','later4-zero','original5-online']:
     page.select_option('#studyRegime',regime);page.locator('#findReplayCases').click();page.wait_for_function("!document.getElementById('replayCase').disabled");page.select_option('#replayCase',index=1)
     for model in ['B0','C1','extended']:
      page.select_option('#liveModel',model);page.locator('#replayPrediction').click();page.wait_for_function("document.getElementById('strictProvenance').textContent.includes('frozen-replay')");assert model+' / ' in page.locator('#strictProvenance').inner_text()
      with page.expect_download() as download:page.locator('#exportResearchRecord').click()
      path=out/(regime+'-'+model+'.json');download.value.save_as(str(path));x=json.loads(path.read_text());assert x['regime']==regime and x['model']==model;records.append(x)
    for assessment in ['helpful','unclear','not-helpful']:
     page.select_option('#researchAssessment',assessment);page.locator('#researchFeedback').click();page.wait_for_function("document.getElementById('researchFeedbackState').textContent.includes('Assessment stored only')")
    page.locator('#researchHistoryRefresh').click();page.wait_for_function("document.querySelectorAll('#researchHistory button').length>0");page.locator('#researchHistory button').first.click();assert 'Record:' in page.locator('#strictProvenance').inner_text()
    # Controlled discovery/error/success UI checks do not call GitHub.
    page.route('**/research/workflows?*',lambda r:r.fulfill(status=429,json={'detail':'Controlled rate limit; no automatic retry'}));page.locator('#discoverWorkflows').click();page.wait_for_function("document.getElementById('strictStatus').textContent.includes('Controlled rate limit')");assert page.locator('#strictPreview').is_disabled()
    page.unroute('**/research/workflows?*');page.route('**/research/workflows?*',lambda r:r.fulfill(json={'workflows':[{'id':'1','name':'Controlled UI fixture','path':'.github/workflows/controlled.yml'}]}));page.locator('#discoverWorkflows').click();page.wait_for_function("!document.getElementById('strictPreview').disabled")
    synthetic=dict(records[0],mode='prospective-cold-preview',notice='Controlled UI response, not a real live prediction',raw_probability=.02);page.route('**/research/preview',lambda r:r.fulfill(json=synthetic));page.locator('#strictPreview').click();page.wait_for_function("document.getElementById('strictStatus').textContent.includes('Controlled UI response')")
    # Keyboard focus and anchor navigation. Disabled legacy form is deliberate.
    for anchor in ['livePanel','researchPanel','historyPanel']:page.locator('a[href="#'+anchor+'"]').click();assert page.evaluate('location.hash')=='#'+anchor
    page.locator('#github_repo_url').focus();page.keyboard.press('Tab');assert page.evaluate('document.activeElement.id')=='github_token';page.keyboard.press('Tab');assert page.evaluate('document.activeElement.id')=='toggleTokenBtn'
    page.locator('a[href="research-v2.html"]').click();page.wait_for_selector('#regime');page.select_option('#regime','original5-online');page.wait_for_function("document.querySelectorAll('#macro tr').length===3");page.select_option('#researchVersion','v1');page.wait_for_selector('#liveModel');page.wait_for_function("document.querySelectorAll('#studyMacro tr').length===3")
    assert page.locator('#github_token').input_value()=='';assert page.locator('#researchFeedback').is_disabled()
    page.unroute('http://127.0.0.1:8000/history?*')
    page.evaluate('loadHistory()')
    live_record=None
    if args.live_public_repository:
     page.unroute('**/research/workflows?*');page.unroute('**/research/preview');page.locator('#github_repo_url').fill(args.live_public_repository);page.locator('#discoverWorkflows').click();page.wait_for_function("!document.getElementById('liveWorkflow').disabled",timeout=60000);page.select_option('#liveWorkflow',args.workflow_id);page.locator('#strictPreview').click();page.wait_for_function("document.getElementById('strictProvenance').textContent.includes('prospective-cold-preview')",timeout=60000)
     with page.expect_download() as download:page.locator('#exportResearchRecord').click()
     path=out/'real-public-preview.json';download.value.save_as(str(path));live_record=json.loads(path.read_text());assert live_record['route']=='no-history';assert live_record['mode']=='prospective-cold-preview';assert live_record['sources'];assert live_record['advisory_risk_score'] is None
    else:
     page.locator('#findReplayCases').click();page.wait_for_function("!document.getElementById('replayPrediction').disabled");page.locator('#replayPrediction').click();page.wait_for_function("document.getElementById('strictProvenance').textContent.includes('frozen-replay')")
    page.locator('#strictLiveCard').scroll_into_view_if_needed();page.screenshot(path=str(out/'stage7-desktop.png'),full_page=True)
    for name,width,height in [('portrait',390,844),('landscape',844,390)]:
     page.set_viewport_size({'width':width,'height':height});page.locator('#strictLiveCard').scroll_into_view_if_needed();page.screenshot(path=str(out/('stage7-mobile-'+name+'.png')),full_page=True);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#changeRepoBtn').click();assert page.locator('#researchFeedback').is_disabled();assert page.locator('#strictProvenance').inner_text()==''
    assert not errors,errors
    result={'status':'passed','actual_model_replays':len(records),'controlled_surfaces':['connection fixture','legacy advice','history pagination','workflow rate-limit and preview display'],'browser_errors':errors,'real_public_preview':live_record is not None,'live_repository':None if live_record is None else live_record['repository'],'viewports':[[1440,1000],[390,844],[844,390]],'limits':['legacy artifact inference disabled','online live unavailable','assessment is not verified CI outcome','single-user local-only']};(out/'acceptance-summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));browser.close()
  finally:server.shutdown();server.server_close();api.terminate();api.wait(timeout=10);log.close()
if __name__=='__main__':main()
