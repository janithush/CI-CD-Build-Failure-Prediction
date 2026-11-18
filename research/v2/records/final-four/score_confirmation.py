from pathlib import Path
import json,hashlib,joblib
import pandas as pd,numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss,log_loss,confusion_matrix
R=Path('/tmp/thesis-final-four');C=R/'confirmation';E=Path('/tmp/thesis-repair/external-results');assert not (C/'RESULTS.json').exists(),'Scores already exist'
for f,h in json.loads((C/'pre-score-hashes.json').read_text()).items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
x=pd.read_csv(C/'frozen-features.csv',dtype={'workflow_id':'string'});counts=x.groupby('repository').size();names=sorted(counts[counts.ge(200)].index);x=x[x.repository.isin(names)].reset_index(drop=True);assert len(names)>=3
p=x[['repository','run_id','run_attempt','commit_id','run_started_at','build_result']].copy();p['constant']=json.load(open(E/'training-state.json'))['constant_prevalence'];models={}
for tag in ['B0','C1']:
 a=joblib.load('/tmp/thesis-repair/final-reproduction/'+tag+'-no-history.joblib');models[tag]=a;p[tag]=a['model'].predict_proba(x[a['features']])[:,1]
p.to_csv(C/'locked-predictions.csv',index=False)
s=json.loads((C/'v2-state.json').read_text());s['performance_exposed']=True;(C/'v2-state.json').write_text(json.dumps(s,indent=2))
rng=np.random.default_rng(42);res={};boot={};diagnostics=[];bins=[]
for repo,g in p.groupby('repository',sort=True):
 y=g.build_result.to_numpy();entry={'rows':len(g),'failures':int(y.sum()),'prevalence':float(y.mean()),'metrics':{}}
 for model in ['B0','C1','constant']:
  prob=np.clip(g[model].to_numpy(),1e-15,1-1e-15);a=models['B0' if model=='constant' else model];pred=prob>=a['source_threshold'];tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel();ece=0
  for b in range(10):
   mask=(prob>=b/10)&((prob<(b+1)/10) if b<9 else (prob<=1));n=int(mask.sum());pp=float(prob[mask].mean()) if n else None;yy=float(y[mask].mean()) if n else None
   if n:ece+=n/len(y)*abs(pp-yy)
   bins.append({'repository':repo,'model':model,'bin_left':b/10,'bin_right':(b+1)/10,'rows':n,'mean_probability':pp,'failure_rate':yy})
  entry['metrics'][model]={'AP':float(average_precision_score(y,prob)),'AP_minus_prevalence':float(average_precision_score(y,prob)-y.mean()),'ROC_AUC':float(roc_auc_score(y,prob)) if len(np.unique(y))==2 else None,'Brier':float(brier_score_loss(y,prob))}
  diagnostics.append({'repository':repo,'model':model,'rows':len(y),'failures':int(y.sum()),'Brier':float(brier_score_loss(y,prob)),'log_loss':float(log_loss(y,prob,labels=[0,1])),'ECE_10_equal_width':ece,'source_threshold':float(a['source_threshold']),'TP':int(tp),'FP':int(fp),'TN':int(tn),'FN':int(fn),'warnings':int(pred.sum()),'warning_rate':float(pred.mean()),'precision':float(tp/(tp+fp)) if tp+fp else None,'recall':float(tp/(tp+fn)) if tp+fn else None,'F1':float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else None,'false_positive_rate':float(fp/(fp+tn)) if fp+tn else None,'false_alarms_per_100_runs':float(100*fp/len(y))})
 entry['AP_delta']=entry['metrics']['C1']['AP']-entry['metrics']['B0']['AP'];groups=list(pd.Series(np.arange(len(g))).groupby(g.commit_id.to_numpy()).indices.values());vals=[]
 for _ in range(1000):
  ix=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
  if len(np.unique(y[ix]))<2:continue
  vals.append(average_precision_score(y[ix],g.C1.to_numpy()[ix])-average_precision_score(y[ix],g.B0.to_numpy()[ix]))
 entry['paired_commit_95']=np.percentile(vals,[2.5,97.5]).tolist();entry['bootstrap_valid']=len(vals);boot[repo]=vals;res[repo]=entry
vals=[]
for _ in range(1000):
 picked=rng.integers(0,len(names),len(names));vals.append(np.mean([rng.choice(boot[names[i]]) for i in picked]))
macro={m:float(np.mean([v['metrics'][m]['AP'] for v in res.values()])) for m in ['B0','C1','constant']};delta=macro['C1']-macro['B0'];ci=np.percentile(vals,[2.5,97.5]).tolist();output={'status':'locked new-cohort confirmation scored once','projects':res,'macro_AP':macro,'macro_AP_delta':delta,'exploratory_project_commit95':ci,'leave_one_project_out_delta':{repo:float(np.mean([v['AP_delta'] for r,v in res.items() if r!=repo])) for repo in names},'reporting_margin':.02,'limits':['Availability-screened roster amended before scoring; original roster failures retained.','Four purposive Python projects, not random or language-independent generalisation.','API head-change features, not complete runtime-source attestation.','Latest API-visible attempt per run; not all historical attempts.','No source calibration, thresholds, models or features changed.','Original five-project negative result remains separate.']};(C/'RESULTS.json').write_text(json.dumps(output,indent=2));pd.DataFrame(diagnostics).to_csv(C/'calibration-warning.csv',index=False);pd.DataFrame(bins).to_csv(C/'reliability-bins.csv',index=False);print(json.dumps(output,indent=2))
