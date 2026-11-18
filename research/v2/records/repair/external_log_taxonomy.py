"""Retained-log audit with per-step timestamp matching; no performance scores."""
from pathlib import Path
from datetime import datetime
import sqlite3,json,re,zipfile,collections,hashlib,time,sys
R=Path(__file__).resolve().parent;D=R/'external-evidence';ansi=re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]');stamp=re.compile(r'^\ufeff?(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z)\s?(.*)$')

def ts(v):
 if not v:return None
 return datetime.fromisoformat(re.sub(r'(\.\d{6})\d+(?=Z)',r'\1',v).replace('Z','+00:00'))

def signals(text):
 clean=ansi.sub('',text)
 pytest_fail=re.findall(r'(?:^|\n).*?\b(\d+) failed\b[^\n]*(?: in | =)',clean)
 unittest_fail=re.findall(r'FAILED \(([^\n]+)\)',clean)
 summary_failed=re.findall(r'(?:^|\n)\s*FAILED ([^\n]+)',clean)
 summary_error=re.findall(r'(?:^|\n)\s*ERROR (?:at |[^\n]+)',clean)
 has_test=bool(re.search(r'\b\d+ passed\b|\bRan \d+ tests? in\b|\b\d+ failed\b|\bcollected \d+ items?\b',clean))
 has_failed=bool(pytest_fail or unittest_fail)
 assertion=False
 if pytest_fail and summary_failed:
  # Require every explicit FAILED summary entry to name AssertionError or
  # an assert expression. No collection/setup ERROR marker is accepted.
  assertion=all(re.search(r' - (?:AssertionError\b|assert\b)',x) for x in summary_failed) and not summary_error and not re.search(r'\b[1-9]\d* errors?\b|ERROR (?:at setup|at teardown|collecting)',clean)
 if unittest_fail:
  assertion=all('failures=' in x and not re.search(r'errors=[1-9]',x) for x in unittest_fail) and 'AssertionError' in clean
 return {'test_output':has_test,'successful_test_summary':bool(re.search(r'\b[1-9]\d* passed\b',clean) or (re.search(r'\bRan [1-9]\d* tests? in\b',clean) and re.search(r'(?:^|\n)\s*OK(?:\s|\(|$)',clean))),'failed_test_summary':has_failed,'assertion_summary_only':bool(assertion),'error_summary':bool(summary_error),'summary_failed_entries':summary_failed[-30:]}

def main():
 e=sqlite3.connect(R/'external-pilot/evidence.sqlite3');c=sqlite3.connect(D/'logs.sqlite3');tax={(x['repository'],x['run_id'],x['run_attempt']):x for x in json.loads((D/'cohort-taxonomy.json').read_text())};stepcats={(x['repository'],x['run_id'],x['run_attempt'],x['job_id'],x['step_number']):x['category'] for x in json.loads((D/'step-taxonomy.json').read_text())};jobs=collections.defaultdict(dict)
 pattern='%/repos/'+sys.argv[1]+'/actions/runs/%/jobs?%' if len(sys.argv)>1 else '%/jobs?%'
 for u,b in e.execute('SELECT url,body FROM responses WHERE url LIKE ?',(pattern,)):
  repo=u.split('/repos/')[1].split('/actions/')[0]
  for j in json.loads(b).get('jobs',[]):jobs[(repo,j['run_id'],j.get('run_attempt',1))][j['id']]=j
 archives={(r,i,a):(status,p,h) for r,i,a,u,status,p,b,h,n,t,err in c.execute('SELECT * FROM archives')};records=[];steps=[]
 suffix='-'+sys.argv[1].replace('/','_') if len(sys.argv)>1 else ''
 version=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();vpath=D/('log-parser'+suffix+'.sha256')
 if vpath.exists() and vpath.read_text()==version:
  rp=D/('retained-log-taxonomy'+suffix+'.json');sp=D/('retained-log-steps'+suffix+'.json')
  if rp.exists():records=json.loads(rp.read_text())
  if sp.exists():steps=json.loads(sp.read_text())
 done={(x['repository'],x['run_id'],x['run_attempt']) for x in records};began=time.monotonic()
 for repo,rid,a,start,conclusion in c.execute('SELECT * FROM cohort ORDER BY repository,run_id'):
  if len(sys.argv)>1 and repo!=sys.argv[1]:continue
  if (repo,rid,a) in done:continue
  if time.monotonic()-began>60:break
  key=(repo,rid,a);status,path,h=archives.get(key,(None,None,None));r={'repository':repo,'run_id':rid,'run_attempt':a,'conclusion':conclusion,'log_status':status,'archive_path':path,'archive_sha256':h,'label':'unresolved_failure' if conclusion=='failure' else 'success_without_verified_test_execution','assertion_only_supported':False,'runtime_source_attestation':'unknown'}
  if status!=200:records.append(r);continue
  logs=collections.defaultdict(list)
  with zipfile.ZipFile(D/path) as z:
   total=sum(x.file_size for x in z.infolist() if '/' not in x.filename and x.filename.endswith('.txt'))
   if total>100*1024*1024:
    r['parser_unresolved_reason']='expanded job logs exceed pre-score 100 MiB per-attempt parse bound; raw archive preserved';r['expanded_job_log_bytes']=total;records.append(r);continue
   for name in z.namelist():
    if '/' in name or not name.endswith('.txt'):continue
    jobname=None;lines=[];previous_checkout=False
    with z.open(name) as stream:
     for rawline in stream:
      line=rawline.decode('utf-8-sig',errors='replace');q=stamp.match(line)
      if not q:continue
      value=ansi.sub('',q.group(2));m=re.search(r'Complete job name: ([^\r\n]+)',value)
      if m:jobname=m.group(1)
      keep=bool(previous_checkout or re.search(r'git log -1 --format=%H|\b\d+ (?:failed|passed|errors?)\b|\bRan \d+ tests? in\b|\bcollected \d+ items?\b|^FAILED |^ERROR |^FAIL: |^FAILED \(|^OK(?:\s|\(|$)|AssertionError',value))
      if keep:lines.append((q.group(1)[:19],value))
      previous_checkout='git log -1 --format=%H' in value
    if jobname:logs[jobname].append((name,lines))
  causes=[];missing=[];test_success=False;assertions=[];checkout=[]
  for j in jobs[key].values():
   choices=logs.get(j['name'],[])
   if j['conclusion'] in ['skipped','cancelled','neutral']:continue
   if len(choices)!=1:missing.append(j['id']);continue
   name,lines=choices[0]
   # Record observed checkout output only, never equate it to tested code.
   for k,(t,line) in enumerate(lines[:-1]):
    if 'git log -1 --format=%H' in line:
     nxt=lines[k+1][1].strip()
     if re.fullmatch('[0-9a-f]{40}',nxt):checkout.append({'job_id':j['id'],'sha':nxt,'log_entry':name,'at':str(t)})
   failedsteps=0
   for s in j.get('steps',[]):
    lo=ts(s.get('started_at'));hi=ts(s.get('completed_at'))
    if not lo or not hi:continue
    # GitHub step timestamps have second resolution. Keep that disclosed.
    text='\n'.join(v for t,v in lines if s['started_at'][:19]<=t<=s['completed_at'][:19])
    signal=signals(text);cat=stepcats.get((*key,j['id'],s['number']),'unresolved')
    if s['conclusion']=='success' and signal['successful_test_summary']:test_success=True
    if s['conclusion']=='failure':
     failedsteps+=1
     if cat!='aggregate_gate' and signal['failed_test_summary']:cat='test_execution'
     if cat!='aggregate_gate':causes.append(cat);assertions.append(cat=='test_execution' and signal['assertion_summary_only'])
     steps.append({'repository':repo,'run_id':rid,'run_attempt':a,'job_id':j['id'],'job_name':j['name'],'step_number':s['number'],'step_name':s['name'],'source_log_entry':name,'started_at':s['started_at'],'completed_at':s['completed_at'],'category':cat,'signals':signal,'interval_uncertainty':'API timestamp resolution is one second; terminal second included'})
   if j['conclusion']=='failure' and failedsteps==0:missing.append(j['id'])
  complete=tax[key]['complete_jobs'];kinds=set(causes)
  if conclusion=='success':r['label']='executed_test_success' if complete and not missing and test_success else r['label']
  elif complete and not missing and kinds:
   if kinds=={'test_execution'}:r['label']='test_execution_only';r['assertion_only_supported']=bool(assertions and all(assertions))
   elif 'test_execution' in kinds:r['label']='mixed_test_and_other'
   elif 'unresolved' not in kinds:r['label']='other_failure'
  r.update({'unmatched_job_ids':missing,'observed_checkout_refs':checkout,'head_sha':tax[key]['head_sha'],'test_success_output':test_success,'failed_categories':sorted(kinds),'runtime_source_attestation':'observed_checkout_only_not_tested_source_proof' if checkout else 'unknown'})
  records.append(r)
 vpath.write_text(version)
 (D/('retained-log-taxonomy'+suffix+'.json')).write_text(json.dumps(records,indent=2));(D/('retained-log-steps'+suffix+'.json')).write_text(json.dumps(steps,indent=2));out=collections.defaultdict(collections.Counter)
 for r in records:out[r['repository']][r['label']]+=1;out[r['repository']]['assertion_only_supported']+=r['assertion_only_supported'];out[r['repository']]['with_observed_checkout_sha']+=bool(r.get('observed_checkout_refs'))
 (D/('retained-log-summary'+suffix+'.json')).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
