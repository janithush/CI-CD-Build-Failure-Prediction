"""Conservative command-backed step taxonomy. No model scoring."""
from pathlib import Path
import sqlite3,json,re,collections,yaml
R=Path(__file__).resolve().parent;D=R/'external-evidence'

def category(command,uses=''):
 s=command.lower();u=uses.lower()
 if 'alls-green' in u or 'normalize_needed_jobs_status' in s:return 'aggregate_gate'
 if not s:return 'unresolved'
 test=bool(re.search(r'\bpytest\b|\bunittest\b|tests/runtests\.py|\bnpm test\b',s))
 setup=bool(re.search(r'\bpip install\b|\bnpm install\b|\bapt.get install\b|\bchoco install\b|\buv pip install\b',s))
 build=bool(re.search(r'\bcibuildwheel\b|\bspin build\b|\bpython -m build\b|\bbuild-pandas\b',s))
 if test and (setup or build):return 'mixed_command'
 if test:return 'test_execution'
 if build:return 'build'
 if setup:return 'setup_environment'
 if re.search(r'\bmypy\b|\bruff\b|lint',s):return 'lint_static'
 if 'benchmark' in s:return 'benchmark'
 return 'unresolved'


def run():
 c=sqlite3.connect(D/'definitions.sqlite3');e=sqlite3.connect(R/'external-pilot/evidence.sqlite3');sources={u:(repo,ref,path,status,body) for u,repo,ref,path,status,body,*_ in c.execute('SELECT * FROM source')};edges=collections.defaultdict(list)
 for a,b,k in c.execute('SELECT * FROM edges'):edges[a].append((b,k))
 roots={(r,i,a):(h,p,u) for r,i,a,h,p,u in c.execute('SELECT * FROM roots')};cache={};steprecords=[];records=[]
 def mappings(root):
  if root in cache:return cache[root]
  seen=set();pending=[root];out=collections.defaultdict(list)
  while pending:
   u=pending.pop()
   if u in seen:continue
   seen.add(u);row=sources.get(u)
   if not row or row[3]!=200:continue
   repo,ref,path,status,body=row
   if not path.endswith(('.yml','.yaml')):continue
   try:obj=yaml.safe_load(body)
   except yaml.YAMLError:continue
   def visit(x):
    if isinstance(x,dict):
     if 'run' in x or 'uses' in x:
      cmd=str(x.get('run',''));uses=str(x.get('uses',''));name=x.get('name')
      cat=category(cmd,uses)
      # Follow only a directly referenced historical shell wrapper for test execution.
      if cat=='unresolved' and cmd:
       refs=re.findall(r'(?<![\w/])(?:\./)?((?:build_tools/|tools/|scripts?/|ci/)[A-Za-z0-9_./-]+\.(?:sh|py))',cmd)
       for p in refs:
        helper='https://raw.githubusercontent.com/'+repo+'/'+ref+'/'+p;h=sources.get(helper)
        if h and h[3]==200 and category(h[4])=='test_execution':cat='test_execution'
      names=[str(name)] if name else []
      if cmd:names.append('Run '+cmd.strip().splitlines()[0])
      if uses:names.append('Run '+uses)
      for n in names:out[n].append({'category':cat,'url':u,'command':cmd,'uses':uses})
     for v in x.values():visit(v)
    elif isinstance(x,list):
     for v in x:visit(v)
   visit(obj);pending.extend(b for b,k in edges[u] if k in ['local_uses','remote_uses_pinned','remote_uses_mutable_ref'])
  cache[root]=out;return out
 jobs=collections.defaultdict(dict)
 for u,b in e.execute("SELECT url,body FROM responses WHERE url LIKE '%/jobs?%'"):
  repo=u.split('/repos/')[1].split('/actions/')[0]
  for j in json.loads(b).get('jobs',[]):jobs[(repo,j['run_id'],j.get('run_attempt',1))][j['id']]=j
 for repo,rid,a,b in e.execute('SELECT * FROM selected_runs'):
  row=json.loads(b);sha,path,root=roots[(repo,rid,a)];mapping=mappings(root);jj=list(jobs[(repo,rid,a)].values());bad=[];goodtest=False;unexplained=False
  complete=e.execute('SELECT all_terminal FROM jobs_complete WHERE repository=? AND run_id=? AND run_attempt=?',(repo,rid,a)).fetchone()[0]
  for j in jj:
   failed=[]
   for s in j.get('steps',[]):
    n=s.get('name','');matches=mapping.get(n,[]);cats={m['category'] for m in matches};cat=next(iter(cats)) if len(cats)==1 else 'unresolved'
    if s.get('conclusion')=='success' and cat=='test_execution':goodtest=True
    if s.get('conclusion')=='failure':
     failed.append(cat);bad.append(cat);steprecords.append({'repository':repo,'run_id':rid,'run_attempt':a,'job_id':j['id'],'job_name':j['name'],'step_name':n,'step_number':s.get('number'),'category':cat,'command_evidence':matches,'job_url':j.get('html_url')})
   if j.get('conclusion')=='failure' and not failed:unexplained=True
  causes=set(bad)-{'aggregate_gate'}
  if row['conclusion']=='success':label='executed_test_success' if complete and goodtest and not bad and all(j.get('conclusion')!='failure' for j in jj) else 'success_without_verified_test_execution'
  elif not complete or unexplained or not causes:label='unresolved_failure'
  elif causes=={'test_execution'}:label='test_execution_only'
  elif 'test_execution' in causes:label='mixed_test_and_other'
  elif 'unresolved' in causes:label='unresolved_failure'
  else:label='other_failure'
  records.append({'repository':repo,'run_id':rid,'run_attempt':a,'conclusion':row['conclusion'],'complete_jobs':bool(complete),'command_taxonomy':label,'failed_categories':sorted(causes),'unexplained_failed_job':unexplained,'definition_url':root,'definition_status':'head_commit_associated_not_runtime_attestation','run_url':row.get('html_url'),'head_sha':sha})
 (D/'step-taxonomy.json').write_text(json.dumps(steprecords,indent=2));(D/'cohort-taxonomy.json').write_text(json.dumps(records,indent=2));summary=collections.defaultdict(collections.Counter)
 for x in records:summary[x['repository']][x['command_taxonomy']]+=1
 (D/'taxonomy-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
