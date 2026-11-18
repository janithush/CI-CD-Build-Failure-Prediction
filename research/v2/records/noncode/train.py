from pathlib import Path
import sys,json,hashlib,joblib,time
import pandas as pd,numpy as np
R=Path('/tmp/thesis-noncode');E=Path('/tmp/thesis-repair/external-results');sys.path.insert(0,str(E))
from improvement_inner import stages,train_branch,BASE,H,T
from improvement_features import C1_COLUMNS
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,confusion_matrix
orig=T.candidates
def bounded(w):
 r=orig(w)
 for m in r.values():
  if 'n_jobs' in m.get_params():m.set_params(n_jobs=2)
 return r
T.candidates=bounded
O=R/'models';O.mkdir(exist_ok=True);contract=json.load(open(R/'feature-contract.json'));cut=pd.Timestamp('2026-07-01',tz='UTC');d=pd.read_csv(R/'source-history.csv',dtype={'workflow_id':'string'})
for c in ['run_started_at','outcome_available_at']:d[c]=pd.to_datetime(d[c],utc=True)
d=d[d.run_started_at.lt(cut)].copy();d['group_id']=d.repository+'::'+d.commit_id;d,bounds=stages(d,cut);d[['repository','run_id','run_attempt','commit_id','stage','run_started_at','outcome_available_at']].to_csv(R/'source-manifest.csv',index=False)
configs={'extended-no-history':[c for c in BASE if c not in H]+C1_COLUMNS+contract['static'],'extended-history':BASE+C1_COLUMNS+contract['static']+contract['history']}
for name,cols in configs.items():
 print('FIT',name,flush=True);train_branch(d,d[d.stage.eq('threshold')].iloc[:10].copy(),cols,O/name)
# Protocol, code, inputs and fitted models locked before target predictions from new models.
paths=[R/'PROTOCOL.md',R/'feature-contract.json',R/'source-manifest.csv',R/'HISTORY_CHECKS.json']+list(R.glob('*.py'))+list(R.glob('*-static.csv'))+list(R.glob('*-history.csv'))+list(O.glob('*.joblib'))
hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths};(R/'PRE_SCORE_HASHES.json').write_text(json.dumps(hashes,indent=2));(R/'fit-state.json').write_text(json.dumps({'bounds':bounds,'source_only_selection':True,'target_scores_exposed':False},indent=2));print('MODELS LOCKED',flush=True)
