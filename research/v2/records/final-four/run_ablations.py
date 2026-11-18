from pathlib import Path
import sys,json,time
import pandas as pd,numpy as np
R=Path('/tmp/thesis-final-four');E=Path('/tmp/thesis-repair/external-results');sys.path.insert(0,str(E))
from improvement_inner import stages,train_branch,BASE,H,T
from improvement_features import add_change_context,C1_COLUMNS
from sklearn.metrics import average_precision_score
O=R/'ablations';O.mkdir(exist_ok=True);orig=T.candidates
def bounded(w):
 r=orig(w)
 for m in r.values():
  if 'n_jobs' in m.get_params():m.set_params(n_jobs=2)
 return r
T.candidates=bounded
base=[c for c in BASE if c not in H];groups={'logs':[c for c in C1_COLUMNS if c.startswith('log1p_')],'ratios':[c for c in C1_COLUMNS if c.startswith('past_mean_')],'proportions':[c for c in C1_COLUMNS if c.endswith('_proportion')]}
configs={'B0':base,'C1':base+C1_COLUMNS}
for k,g in groups.items():configs['B0-plus-'+k]=base+g;configs['C1-minus-'+k]=base+[c for c in C1_COLUMNS if c not in g]
d=pd.read_csv(E/'five_features_improvement.csv',dtype={'workflow_id':'string'})
for col in ['run_started_at','outcome_available_at']:d[col]=pd.to_datetime(d[col],utc=True)
d['group_id']=d.repository+'::'+d.commit_id
start=time.monotonic();cut=pd.Timestamp('2026-04-01',tz='UTC');end=pd.Timestamp('2026-07-01',tz='UTC')
for repo in sorted(d.repository.unique()):
 F=O/repo.replace('/','_');F.mkdir(exist_ok=True)
 source=add_change_context(d[d.repository.ne(repo)&d.run_started_at.lt(cut)].copy());source,bounds=stages(source,cut)
 target=add_change_context(d[d.repository.eq(repo)&d.run_started_at.ge(cut)&d.run_started_at.lt(end)&d.outcome_available_at.lt(end)].sort_values(['run_started_at','run_id','run_attempt'],kind='stable').copy())
 source[['repository','run_id','run_attempt','stage']].to_csv(F/'source-manifest.csv',index=False)
 target[['repository','run_id','run_attempt','commit_id','run_started_at','build_result']].to_csv(F/'target-manifest.csv',index=False)
 for name,cols in configs.items():
  if (F/(name+'-metrics.json')).exists():continue
  if time.monotonic()-start>75:print('CHECKPOINT time limit',flush=True);sys.exit(0)
  print('START',repo,name,flush=True)
  try:
   meta,p=train_branch(source,target,cols,F/name);result={'feasible':True,'held_project':repo,'configuration':name,'rows':len(target),'failures':int(target.build_result.sum()),'ap':float(average_precision_score(target.build_result,p)),'model':meta['selected_model'],'boundaries':bounds,'target_change_context':'reset at April1 boundary; strictly earlier unique changes only'}
  except ValueError as e:result={'feasible':False,'reason':str(e),'held_project':repo,'configuration':name}
  (F/(name+'-metrics.json')).write_text(json.dumps(result,indent=2));print('DONE',result,flush=True)
print('ALL ABLATIONS COMPLETE',flush=True)
