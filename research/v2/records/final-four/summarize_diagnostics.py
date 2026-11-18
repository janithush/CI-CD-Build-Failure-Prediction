from pathlib import Path
import json,sys,hashlib,zipfile
import pandas as pd,numpy as np,joblib
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss,confusion_matrix,roc_auc_score
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/tmp/thesis-final-four');E=Path('/tmp/thesis-repair/external-results');O=R/'diagnostics';O.mkdir(exist_ok=True)
# Verify all held-out source-only ablation folds against their saved prediction files.
rows=[]
for f in sorted((R/'ablations').glob('*/*-metrics.json')):
 j=json.loads(f.read_text());assert j['feasible'];name=j['configuration'];p=pd.read_csv(f.parent/(name+'.csv'));target=pd.read_csv(f.parent/'target-manifest.csv');assert len(p)==len(target)==j['rows'];assert abs(average_precision_score(target.build_result,p.probability)-j['ap'])<1e-12
 source=pd.read_csv(f.parent/'source-manifest.csv');assert not source.repository.eq(j['held_project']).any();assert not set(source.repository+'::'+source.run_id.astype(str)).intersection(set(target.repository+'::'+target.run_id.astype(str)))
 rows.append(j)
a=pd.DataFrame(rows);assert len(a)==40 and a.held_project.nunique()==5 and a.configuration.nunique()==8
p=a.pivot(index='held_project',columns='configuration',values='ap');p.to_csv(O/'ablation-project-AP.csv');delta=p.subtract(p.B0,axis=0);delta.to_csv(O/'ablation-project-delta-vs-B0.csv');summary=pd.DataFrame({'macro_AP':p.mean(),'macro_delta_vs_B0':delta.mean(),'projects_positive_vs_B0':delta.gt(0).sum()}).sort_values('macro_AP',ascending=False);summary.to_csv(O/'ablation-summary.csv')
text='# C1 feature-group ablations\n\n18 November 2026. All forty fixed fits completed and predictions/holdout separation verified. Source development data only; no old or new external score selected these configurations. Each source fit selects from the original six learned settings and uses separate strict calibration/threshold stages. These are diagnostic refitted-pipeline ablations, not a causal isolated feature effect. Held-project earlier-change context is reset at the April 1 boundary.\n\n'+summary.to_markdown()+'\n\n## Per-development-project AP\n\n'+p.to_markdown()+'\n\nThe configurations and five folds were fixed before fitting. All results are shown, including worse settings. No ablation winner replaces the locked B0/C1 confirmation models. Five source folds share training data and are not five independent confirmations. The original external C1 negative result remains unchanged.\n'
(O/'ABLATION_REPORT.md').write_text(text)
# Reliability and source-threshold diagnostics on saved external predictions.
constant=json.loads((E/'training-state.json').read_text())['constant_prevalence'];metrics=[];bins=[]
for regime,filename in [('zero-label','predictions-zero_label.csv'),('online','predictions-online.csv')]:
 d=pd.read_csv(E/filename);f=pd.read_csv(E/('features-'+regime+'.csv'));assert len(d)==len(f)
 for c in ['repository','run_id','run_attempt']:assert d[c].astype(str).equals(f[c].astype(str))
 for repo,g in d.groupby('repository',sort=True):
  y=g.build_result.to_numpy(dtype=int)
  for model in ['constant','B0','C1']:
   prob=np.repeat(constant,len(g)) if model=='constant' else g[model].to_numpy();prob=np.clip(prob,1e-15,1-1e-15)
   branch_no=json.loads((E/(('B0' if model=='constant' else model)+'-no-history.json')).read_text())['source_threshold']
   if regime=='online':
    branch_yes=json.loads((E/(('B0' if model=='constant' else model)+'-history.json')).read_text())['source_threshold'];threshold=np.where(f.loc[g.index,'history_rich'],branch_yes,branch_no)
   else:threshold=np.repeat(branch_no,len(g))
   # Constant control warning counts use B0's fixed source policy, not a fitted target threshold.
   predicted=prob>=threshold;tn,fp,fn,tp=confusion_matrix(y,predicted,labels=[0,1]).ravel();ece=0
   for b in range(10):
    mask=(prob>=b/10)&((prob<(b+1)/10) if b<9 else (prob<=1));n=int(mask.sum());pred=float(prob[mask].mean()) if n else None;obs=float(y[mask].mean()) if n else None
    if n:ece+=n/len(y)*abs(pred-obs)
    bins.append({'regime':regime,'repository':repo,'model':model,'bin_left':b/10,'bin_right':(b+1)/10,'rows':n,'mean_probability':pred,'failure_rate':obs})
   metrics.append({'regime':regime,'repository':repo,'model':model,'rows':len(y),'failures':int(y.sum()),'prevalence':float(y.mean()),'AP':float(average_precision_score(y,prob)),'Brier':float(brier_score_loss(y,prob)),'log_loss':float(log_loss(y,prob,labels=[0,1])),'ECE_10_equal_width':ece,'TP':int(tp),'FP':int(fp),'TN':int(tn),'FN':int(fn),'warnings':int(predicted.sum()),'warning_rate':float(predicted.mean()),'precision':float(tp/(tp+fp)) if tp+fp else None,'recall':float(tp/(tp+fn)) if tp+fn else None,'F1':float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else None,'false_positive_rate':float(fp/(fp+tn)) if fp+tn else None,'false_alarms_per_100_runs':100*float(fp/len(y)),'threshold_policy':'model source-only, history routing in online; constant uses B0 policy'})
m=pd.DataFrame(metrics);b=pd.DataFrame(bins);m.to_csv(O/'calibration-warning-by-project.csv',index=False);b.to_csv(O/'reliability-bins.csv',index=False)
for regime in ['zero-label','online']:
 fig,axes=plt.subplots(1,5,figsize=(16,3.5),sharex=True,sharey=True)
 for ax,repo in zip(axes,sorted(d.repository.unique())):
  ax.plot([0,1],[0,1],color='#777',ls='--',lw=1)
  for model,color in [('B0','#222222'),('C1','#277b68'),('constant','#ae612a')]:
   q=b[(b.regime==regime)&(b.repository==repo)&(b.model==model)&b.rows.gt(0)];ax.plot(q.mean_probability,q.failure_rate,'o-',label=model,color=color,ms=4)
  ax.set_title(repo.split('/')[-1]);ax.set_xlabel('Mean predicted failure probability');ax.set_xlim(0,1);ax.set_ylim(0,1);ax.grid(alpha=.2)
 axes[0].set_ylabel('Observed failure fraction');axes[-1].legend(fontsize=8);fig.suptitle('Reliability: '+regime+' (equal-width bins; sparse bins remain noisy)');fig.tight_layout();fig.savefig(O/('reliability-'+regime+'.png'),dpi=160);plt.close(fig)
macro=m.groupby(['regime','model'])[['Brier','log_loss','ECE_10_equal_width','warning_rate','recall','precision','false_alarms_per_100_runs']].mean();macro.to_csv(O/'calibration-warning-macro.csv')
(O/'CALIBRATION_WARNING_REPORT.md').write_text('# Calibration and warning analysis\n\n18 November 2026. Existing five-project external cohort only; new-cohort addition is still pending. All thresholds and calibration are source-only. No target threshold tuning or recalibration. Ten fixed equal-width reliability bins include counts, with no claim of stable calibration from sparse bins. ECE depends on binning. Constant uses source-fit prevalence '+str(constant)+'. Its warning counts use the fixed B0 policy for comparison, not its own target-optimized threshold.\n\n'+macro.to_markdown()+'\n\nThese are equal-project descriptive means. Per-project counts and confusion matrices are in calibration-warning-by-project.csv. Precision is undefined when no warnings occur and is left blank, not set to a favourable value. The figures do not show time savings, utility, safe skipping or prospective validation. Source alert thresholds may transfer poorly; model ranking and calibration are different questions. Original negative C1 transfer findings remain unchanged.\n')
print('ABLATIONS\n',summary.to_string());print('CALIBRATION\n',macro.to_string())
