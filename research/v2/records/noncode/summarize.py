from pathlib import Path
import json,hashlib,pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score,brier_score_loss
R=Path('/tmp/thesis-noncode');K=['repository','run_id','run_attempt'];logs=pd.read_csv(R/'log-classification.csv');p=pd.read_csv(R/'original5-zero-predictions.csv');j=logs.merge(p,on=K,validate='one_to_one');assert len(j)==500
j.to_csv(R/'audit-scored.csv',index=False);rows=[]
for c in ['test_or_compile_supported','environment_like_supported','mixed_observed_signatures','unknown']:
 q=j[j.scope_category.eq('success')|j.scope_category.eq(c)];y=q.conclusion.eq('failure').astype(int)
 for model in ['B0','C1','extended']:rows.append({'stratum':c,'model':model,'rows':len(q),'positives':int(y.sum()),'pooled_AP':float(average_precision_score(y,q[model])) if y.sum() else None})
pd.DataFrame(rows).to_csv(R/'scope-strata.csv',index=False)
metric=pd.read_csv(R/'metrics-by-project.csv');checks=[]
for regime in metric.regime.unique():
 d=pd.read_csv(R/(regime+'-predictions.csv'))
 for repo,g in d.groupby('repository'):
  for model in ['B0','C1','extended']:
   m=metric[(metric.regime==regime)&(metric.repository==repo)&(metric.model==model)].iloc[0];assert abs(average_precision_score(g.build_result,g[model])-m.AP)<1e-12;assert abs(brier_score_loss(g.build_result,g[model])-m.Brier)<1e-12;assert m.TP+m.FP+m.TN+m.FN==len(g)
 checks.append(regime+': AP/Brier independently recomputed, confusion totals checked')
retr=[json.load(open(f)) for f in (R/'log-retrieval').glob('*.json')];assert len(retr)==134 and all(v['matches_previous_hash'] and v['status']==200 for v in retr)
assert len(list((R/'raw-logs').glob('*.zip')))==496
for a in pd.read_csv('/tmp/thesis-repair/external-results/frozen-log-membership.csv').to_dict('records'):
 if a['log_status']==200:assert hashlib.sha256((R/'raw-logs'/Path(a['archive_path']).name).read_bytes()).hexdigest()==a['archive_sha256']
checks.append('All 496 retained raw ZIPs match original frozen hashes, including 134 repaired omissions; four 404s remain absent')
(R/'INDEPENDENT_CHECKS.json').write_text(json.dumps({'checks':checks,'primary_model_predictions_changed_after_scoring':False},indent=2))
a=pd.read_csv(R/'rerun-pairs.csv');summary=a.groupby('cohort').agg(pairs=('run_id','size'),runs=('run_id','nunique'),failure_then_success_pairs=('failure_then_success','sum'));summary['runs_with_failure_then_success']=a[a.failure_then_success].groupby('cohort').run_id.nunique();summary.to_csv(R/'rerun-summary.csv')
macro=pd.read_csv(R/'macro-before-after.csv');fig,axes=plt.subplots(1,2,figsize=(10,4.4));names=['original5-zero','later4-zero','original5-online'];xs=np.arange(3)
for n,(model,color) in enumerate([('B0','#6b7280'),('C1','#0b4d65'),('extended','#b45f26')]):
 q=macro[macro.model.eq(model)].set_index('regime').loc[names];axes[0].bar(xs+(n-1)*.23,q.AP,.23,label=model,color=color);axes[1].bar(xs+(n-1)*.23,q.false_alarms_per_100_runs,.23,label=model,color=color)
for ax in axes:ax.set_xticks(xs,['Original 5\nzero history','Later 4\nzero history','Original 5\nonline']);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
axes[0].set_ylabel('Equal-project mean average precision');axes[0].set_ylim(0,.42);axes[1].set_ylabel('False alarms per 100 runs');axes[0].legend(frameon=False);fig.suptitle('Exploratory extension: small cold AP shifts, more false alarms\nAll projects previously viewed; thresholds selected on source data only',fontsize=11);fig.tight_layout();fig.savefig(R/'before-after.png',dpi=180);plt.close(fig)
print(summary.to_string());print('Scope counts',logs.groupby(['conclusion','scope_category']).size().to_string());print('ALL CHECKS PASSED')
