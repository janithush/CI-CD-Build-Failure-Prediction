from pathlib import Path
import json,hashlib,sys,joblib
import pandas as pd,numpy as np
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,confusion_matrix
R=Path('/tmp/thesis-noncode');E=Path('/tmp/thesis-repair/external-results');K=['repository','run_id','run_attempt'];O=R/'models'
assert not (R/'RESULTS.json').exists(),'Target predictions already exposed'
for p,h in json.load(open(R/'PRE_SCORE_HASHES.json')).items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
models={n:joblib.load(O/(n+'.joblib')) for n in ['extended-no-history','extended-history']};metrics=[];allpred=[];bins=[]
for regime,featurefile,oldfile in [('original5-zero','original5-zero-static.csv',E/'predictions-zero_label.csv'),('original5-online','original5-online-history.csv',E/'predictions-online.csv'),('later4-zero','later4-zero-static.csv',Path('/tmp/thesis-final-four/confirmation/locked-predictions.csv'))]:
 d=pd.read_csv(R/featurefile,dtype={'workflow_id':'string'});old=pd.read_csv(oldfile);assert d[K].astype(str).equals(old[K].astype(str));assert d.build_result.equals(old.build_result)
 a=models['extended-no-history'];p=a['model'].predict_proba(d[a['features']])[:,1];threshold=np.repeat(a['source_threshold'],len(d))
 if regime.endswith('online'):
  b=models['extended-history'];hp=b['model'].predict_proba(d[b['features']])[:,1];p=np.where(d.history_rich,hp,p);threshold=np.where(d.history_rich,b['source_threshold'],a['source_threshold'])
 pred=old[K+['commit_id','run_started_at','build_result','B0','C1']].copy();pred['extended']=p;pred['extended_threshold']=threshold;pred['regime']=regime
 for tag in ['B0','C1']:
  nh=joblib.load('/tmp/thesis-repair/final-reproduction/'+tag+'-no-history.joblib');th=np.repeat(nh['source_threshold'],len(d));fresh=nh['model'].predict_proba(d[nh['features']])[:,1]
  if regime.endswith('online'):
   yh=joblib.load('/tmp/thesis-repair/final-reproduction/'+tag+'-history.joblib');fresh=np.where(d.history_rich,yh['model'].predict_proba(d[yh['features']])[:,1],fresh);th=np.where(d.history_rich,yh['source_threshold'],th)
  assert np.max(np.abs(fresh-pred[tag]))<1e-12,(regime,tag);pred[tag+'_threshold']=th
 pred.to_csv(R/(regime+'-predictions.csv'),index=False);allpred.append(pred)
 for repo,g in pred.groupby('repository'):
  y=g.build_result.to_numpy()
  for model in ['B0','C1','extended']:
   prob=g[model].to_numpy();warning=prob>=g[model+'_threshold'].to_numpy();tn,fp,fn,tp=confusion_matrix(y,warning,labels=[0,1]).ravel();metrics.append({'regime':regime,'repository':repo,'model':model,'rows':len(g),'failures':int(y.sum()),'AP':float(average_precision_score(y,prob)),'Brier':float(brier_score_loss(y,prob)),'log_loss':float(log_loss(y,np.clip(prob,1e-15,1-1e-15),labels=[0,1])),'warning_rate':float(warning.mean()),'false_alarms_per_100_runs':100*fp/len(g),'TP':int(tp),'FP':int(fp),'TN':int(tn),'FN':int(fn)})
   for b in range(10):
    mask=(prob>=b/10)&(prob<(b+1)/10 if b<9 else prob<=1);bins.append({'regime':regime,'repository':repo,'model':model,'bin':b,'rows':int(mask.sum()),'mean_probability':float(prob[mask].mean()) if mask.any() else None,'observed_failure':float(y[mask].mean()) if mask.any() else None})
m=pd.DataFrame(metrics);m.to_csv(R/'metrics-by-project.csv',index=False);pd.DataFrame(bins).to_csv(R/'reliability-bins.csv',index=False);macro=m.groupby(['regime','model'])[['AP','Brier','warning_rate','false_alarms_per_100_runs']].mean();macro.to_csv(R/'macro-before-after.csv');print(macro.to_string())
# Exploratory paired project-and-commit interval; not new untouched confirmation.
rng=np.random.default_rng(42);intervals={}
for regime,pred in pd.concat(allpred).groupby('regime'):
 boot={}
 for repo,g in pred.groupby('repository'):
  g=g.reset_index(drop=True);groups=list(g.groupby('commit_id').indices.values());vals=[]
  for _ in range(500):
   ii=np.concatenate([groups[k] for k in rng.integers(0,len(groups),len(groups))]);y=g.build_result.to_numpy()[ii]
   if len(np.unique(y))==2:vals.append(average_precision_score(y,g.extended.to_numpy()[ii])-average_precision_score(y,g.C1.to_numpy()[ii]))
  boot[repo]=vals
 repos=list(boot);v=[np.mean([rng.choice(boot[repos[k]]) for k in rng.integers(0,len(repos),len(repos))]) for _ in range(500)];intervals[regime]=np.percentile(v,[2.5,97.5]).tolist()
# Fixed 500-case log audit strata, not a causal endpoint.
logs=pd.read_csv(R/'log-classification.csv');joined=logs.merge(allpred[0],on=K,validate='one_to_one');assert len(joined)==500;joined.to_csv(R/'audit-scored.csv',index=False);strata=[]
for category in ['test_or_compile_supported','environment_like_supported','mixed_observed_signatures','unknown']:
 q=joined[joined.scope_category.eq('success')|joined.scope_category.eq(category)];y=q.conclusion.eq('failure').astype(int)
 for model in ['B0','C1','extended']:
  strata.append({'stratum':category,'model':model,'rows':len(q),'positives':int(y.sum()),'pooled_AP':float(average_precision_score(y,q[model])) if y.sum() else None,'limitation':'selected post-outcome evidence stratum against all observed provider successes, not causal labels, balanced projects or representative prevalence'})
pd.DataFrame(strata).to_csv(R/'scope-strata.csv',index=False)
res={'macro':macro.reset_index().to_dict('records'),'exploratory_paired_commit_project_interval_extended_minus_C1':intervals,'limits':['All external projects already viewed; descriptive extension, not untouched confirmation.','Broad provider workflow failure remains primary.','Cause categories are signatures, not causal labels.','Source updated_at proxy, partial runtime identity and missing logs remain.'],'baseline_predictions_independently_reproduced':True}
(R/'RESULTS.json').write_text(json.dumps(res,indent=2));state=json.load(open(R/'fit-state.json'));state['target_scores_exposed']=True;(R/'fit-state.json').write_text(json.dumps(state,indent=2));print(json.dumps(intervals,indent=2))
