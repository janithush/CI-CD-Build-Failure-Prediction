from pathlib import Path
import sys,json,pandas as pd,numpy as np
R=Path('/tmp/thesis-repair/external-results');sys.path.insert(0,str(R));from improvement_inner import stages,train_branch,BASE,H,T
from improvement_features import C1_COLUMNS
from sklearn.metrics import average_precision_score
orig=T.candidates
def bounded(w):
 r=orig(w)
 for m in r.values():
  if 'n_jobs' in m.get_params():m.set_params(n_jobs=2)
 return r
T.candidates=bounded
O=Path('/tmp/thesis-repair/final-reproduction');O.mkdir(exist_ok=True)
s=pd.read_csv(R/'five_features_improvement.csv',dtype={'workflow_id':'string'})
for c in ['run_started_at','outcome_available_at']:s[c]=pd.to_datetime(s[c],utc=True)
s=s[s.run_started_at.lt(pd.Timestamp('2026-07-01',tz='UTC'))].copy();s['group_id']=s.repository+'::'+s.commit_id;s,bounds=stages(s,pd.Timestamp('2026-07-01',tz='UTC'))
m=pd.read_csv(R/'source-manifest.csv');assert s[['repository','run_id','run_attempt','stage']].astype(str).reset_index(drop=True).equals(m[['repository','run_id','run_attempt','stage']].astype(str))
target=s[s.stage.eq('threshold')].iloc[:10].copy();records={};models={}
for name,cols in {'B0-history':BASE,'B0-no-history':[c for c in BASE if c not in H],'C1-history':BASE+C1_COLUMNS,'C1-no-history':[c for c in BASE if c not in H]+C1_COLUMNS}.items():
 print('START',name,flush=True);result,p=train_branch(s,target,cols,O/name);old=pd.read_csv(R/(name+'.csv'));records[name]={'max_abs_source_prediction_difference':float(np.max(np.abs(p-old.probability.to_numpy()))),'model':result['selected_model']};print(records[name],flush=True)
 import joblib
 models[name]=joblib.load(O/(name+'.joblib'))
results={}
for regime in ['zero-label','online']:
 d=pd.read_csv(R/('features-'+regime+'.csv'),dtype={'workflow_id':'string'});old=pd.read_csv(R/('predictions-'+regime.replace('-','_')+'.csv'));output=d[['repository','run_id','run_attempt','build_result']].copy()
 for tag in ['B0','C1']:
  p={}
  for branch in ['history','no-history']:
   a=models[tag+'-'+branch];p[branch]=a['model'].predict_proba(d[a['features']])[:,1]
  prob=p['no-history'] if regime=='zero-label' else np.where(d.history_rich,p['history'],p['no-history']);output[tag]=prob
  records[tag+'_'+regime]={'max_abs_external_prediction_difference':float(np.max(np.abs(prob-old[tag].to_numpy())))}
 output.to_csv(O/('predictions-'+regime+'.csv'),index=False)
 results[regime]={repo:{tag:float(average_precision_score(g.build_result,g[tag])) for tag in ['B0','C1']} for repo,g in output.groupby('repository')}
 results[regime]['macro']={tag:float(np.mean([v[tag] for v in results[regime].values()])) for tag in ['B0','C1']}
 results[regime]['macro']['delta']=results[regime]['macro']['C1']-results[regime]['macro']['B0']
(O/'reproduction.json').write_text(json.dumps({'prediction_checks':records,'results':results,'boundaries':bounds},indent=2));print(json.dumps(results,indent=2),flush=True)
