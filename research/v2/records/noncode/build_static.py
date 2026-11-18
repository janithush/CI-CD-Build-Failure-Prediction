from pathlib import Path
import json,sqlite3,pandas as pd,numpy as np,yaml,re,hashlib,heapq,math
R=Path('/tmp/thesis-noncode');E=Path('/tmp/thesis-repair/external-results');K=['repository','run_id','run_attempt']
STATIC=['run_hour_sin','run_hour_cos','run_week_sin','run_week_cos','attempt_index','yaml_missing','defined_jobs','matrix_axis_count','matrix_axis_product_sum','matrix_include_entries','matrix_exclude_entries','reusable_jobs','dynamic_definition','declares_linux','declares_windows','declares_macos','declares_self_hosted']
HIST=['released_workflow_failure_streak','prior_same_head_count','prior_same_head_failure_fraction','released_workflow_discordant_pair_count','released_workflow_observed_pair_count','released_workflow_discordance_fraction']
frames={'source':pd.read_csv(E/'five_features_improvement.csv',dtype={'workflow_id':'string'}),'original5-zero':pd.read_csv(E/'features-zero-label.csv',dtype={'workflow_id':'string'}),'original5-online':pd.read_csv(E/'features-online.csv',dtype={'workflow_id':'string'}),'later4-zero':pd.read_csv('/tmp/thesis-final-four/confirmation/frozen-features.csv',dtype={'workflow_id':'string'})};counts=frames['later4-zero'].groupby('repository').size();frames['later4-zero']=frames['later4-zero'][frames['later4-zero'].repository.isin(counts[counts.ge(200)].index)].reset_index(drop=True)
cache=[json.load(open(p)) for p in (R/'responses').glob('*.json')];defs={}
c=sqlite3.connect('/tmp/thesis-repair/source/research-checkpoint/audit/definition_audit.sqlite3')
for repo,sha,path,content in c.execute('select d.repository,d.commit_id,d.path,b.content from definitions d join blobs b on b.blob=d.blob'):defs[(repo,sha,path)]=content
c=sqlite3.connect(R/'external-definitions.sqlite3')
for repo,ref,path,body in c.execute('select repository,ref,path,body from source where status=200'):defs[(repo,ref,path)]=body
for v in cache:
 if v['kind']=='definition' and v['status']==200:
  s=v['url'].split('raw.githubusercontent.com/')[1].split('/');defs[('/'.join(s[:2]),s[2],'/'.join(s[3:]))]=v['data']
features={}
def static(content):
 out={c:np.nan for c in STATIC[5:]};out['yaml_missing']=1
 if content is None:return out
 try:d=yaml.safe_load(content)
 except yaml.YAMLError:return out
 if not isinstance(d,dict) or not isinstance(d.get('jobs'),dict):return out
 jobs=d['jobs'];out.update({c:0. for c in STATIC[5:]});out['defined_jobs']=len(jobs)
 for j in jobs.values():
  if not isinstance(j,dict):continue
  if 'uses' in j:out['reusable_jobs']+=1
  matrix=(j.get('strategy') or {}).get('matrix',{}) if isinstance(j.get('strategy',{}),dict) else {}
  if not isinstance(matrix,dict):out['dynamic_definition']=1;matrix={}
  axes=[v for k,v in matrix.items() if k not in ['include','exclude']];out['matrix_axis_count']+=len(axes)
  if axes:
   if all(isinstance(v,list) and all('${{' not in str(z) for z in v) for v in axes):out['matrix_axis_product_sum']+=math.prod(len(v) for v in axes)
   else:out['dynamic_definition']=1;out['matrix_axis_product_sum']=np.nan
  for label in ['include','exclude']:
   v=matrix.get(label,[])
   if isinstance(v,list):out['matrix_'+label+'_entries']+=len(v)
   else:out['dynamic_definition']=1
  text=json.dumps({'runs-on':j.get('runs-on'),'matrix':matrix}).lower()
  if '${{' in text:out['dynamic_definition']=1
  for key,rx in [('linux','ubuntu|linux'),('windows','windows'),('macos','macos'),('self_hosted','self-hosted')]:out['declares_'+key]=max(out['declares_'+key],int(bool(re.search(rx,text))))
 return out
# All exposed historical attempt evidence, joined to the fixed latest observed row.
rows=[]
for name,d in frames.items():
 if name=='original5-online':continue
 rows+=d[K+['workflow_id','commit_id','conclusion','run_started_at','outcome_available_at']].assign(cohort=name).to_dict('records')
latest={(r['repository'],int(r['run_id'])):r for r in rows};previous=[];bad=[]
for v in cache:
 if v['kind']!='attempt' or v['status']!=200:continue
 a=v['data'];s=v['url'].split('/repos/')[1].split('/actions/');repo=s[0];rid=int(s[1].split('/')[1]);key=(repo,rid);parent=latest.get(key)
 if parent is None or a.get('id')!=rid or a.get('run_attempt')!=int(v['url'].split('/')[-1]):bad.append(v['url']);continue
 previous.append({'repository':repo,'run_id':rid,'run_attempt':a['run_attempt'],'workflow_id':str(a.get('workflow_id')),'commit_id':a.get('head_sha'),'conclusion':a.get('conclusion'),'run_started_at':a.get('run_started_at'),'outcome_available_at':a.get('updated_at'),'url':v['url'],'cohort':parent['cohort']})
attempts=pd.DataFrame(rows+previous).drop_duplicates(K).sort_values(K);attempts.to_csv(R/'attempt-evidence.csv',index=False);pairs=[]
for (repo,rid),g in attempts.groupby(['repository','run_id']):
 if len(g)<2:continue
 g=g.sort_values('run_attempt')
 for i,a in enumerate(g.to_dict('records')):
  for b in g.to_dict('records')[i+1:]:
   same=a['commit_id']==b['commit_id'] and str(a['workflow_id'])==str(b['workflow_id']);lo=pd.to_datetime(a['outcome_available_at'],utc=True,errors='coerce');hi=pd.to_datetime(b['outcome_available_at'],utc=True,errors='coerce');release=max(lo,hi) if pd.notna(lo) and pd.notna(hi) else pd.NaT
   pairs.append({'repository':repo,'run_id':rid,'workflow_id':str(b['workflow_id']),'commit_id':b['commit_id'],'earlier_attempt':a['run_attempt'],'later_attempt':b['run_attempt'],'earlier_conclusion':a['conclusion'],'later_conclusion':b['conclusion'],'same_recorded_head_and_workflow':same,'failure_then_success':same and a['conclusion']=='failure' and b['conclusion']=='success','discordant':same and {a['conclusion'],b['conclusion']}=={'failure','success'},'available_at':release if pd.notna(release) and lo>=pd.to_datetime(a['run_started_at'],utc=True,errors='coerce') and hi>=pd.to_datetime(b['run_started_at'],utc=True,errors='coerce') else pd.NaT,'cohort':b['cohort']})
pairs=pd.DataFrame(pairs);pairs.to_csv(R/'rerun-pairs.csv',index=False)
def enrich(d,name):
 d=d.copy().reset_index(drop=True);t=pd.to_datetime(d.run_started_at,utc=True);hour=t.dt.hour+t.dt.minute/60;week=t.dt.dayofweek+hour/24
 for col,v in [('run_hour_sin',np.sin(2*np.pi*hour/24)),('run_hour_cos',np.cos(2*np.pi*hour/24)),('run_week_sin',np.sin(2*np.pi*week/7)),('run_week_cos',np.cos(2*np.pi*week/7)),('attempt_index',d.run_attempt)]:d[col]=v
 stat=[]
 for row in d.to_dict('records'):
  key=(row['repository'],row['commit_id'],str(row['workflow_path']).split('@')[0]);content=defs.get(key);h=hashlib.sha256(content.encode()).hexdigest() if content is not None else 'missing'
  if h not in features:features[h]=static(content)
  stat.append(features[h])
 for col in STATIC[5:]:d[col]=[v[col] for v in stat]
 return d
for name,d in frames.items():
 q=enrich(d,name);q.to_csv(R/(name+'-static.csv'),index=False);print(name,len(q),'definitions',int(q.yaml_missing.eq(0).sum()),flush=True)
(R/'feature-contract.json').write_text(json.dumps({'static':STATIC,'history':HIST,'bad_attempt_identity_urls':bad,'definition_count':len(defs),'unique_parsed_contents':len(features)},indent=2))
print('rerun pairs',len(pairs),'discordant',int(pairs.discordant.sum()),'fail_then_success',int(pairs.failure_then_success.sum()),flush=True)
