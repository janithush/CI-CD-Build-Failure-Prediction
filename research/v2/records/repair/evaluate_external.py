"""Frozen external evaluation. Refuses existing results. No fitting or selection."""
from pathlib import Path
import hashlib,json,joblib
import numpy as np,pandas as pd
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss
R=Path(__file__).resolve().parent;D=R/'external-evaluation';E=R/'external-evidence';KEYS=['repository','run_id','run_attempt'];OUT=D/'external-results.json'

def score(y,p):
 return {'ap':float(average_precision_score(y,p)),'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None,'brier':float(brier_score_loss(y,p))}

def main():
 if OUT.exists():raise RuntimeError('External scores exist. Never overwrite or retune.')
 hashes=json.load(open(D/'pre-score-hashes.json'))
 for p,h in hashes.items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
 for f in ['features-zero-label.csv','features-online.csv']:
  assert len(pd.read_csv(D/f))==2500
 training=json.load(open(D/'training-state.json'));assert not training['external_scores_computed'];prior=training['constant_prevalence'];models={n:joblib.load(D/(n+'.joblib')) for n in training['branches']}
 regimes={};cols=KEYS+['commit_id','run_started_at','build_result','complete_jobs','workflow_prior_runs']
 for regime,file in [('zero_label','features-zero-label.csv'),('online','features-online.csv')]:
  x=pd.read_csv(D/file,dtype={'workflow_id':'string'});x['group_id']=x.repository+'::'+x.commit_id
  assert len(x)==len(x.drop_duplicates(KEYS))==2500
  rich=x.workflow_prior_runs.ge(5) if regime=='online' else np.zeros(len(x),dtype=bool)
  if regime=='zero_label':assert x.workflow_prior_runs.eq(0).all()
  p={}
  for n,v in models.items():p[n]=v['model'].predict_proba(x[v['features']])[:,1]
  rows=x[cols+['group_id']].copy();rows['B0']=np.where(rich,p['B0-history'],p['B0-no-history']);rows['C1']=np.where(rich,p['C1-history'],p['C1-no-history']);rows['constant']=prior;rows['online_prior']=x.workflow_prior_failure_rate.fillna(prior);rows['history_branch']=rich
  rows.to_csv(D/('predictions-'+regime+'.csv'),index=False);regimes[regime]=rows
 # Freeze labels and provenance hashes before opening model metrics.
 log=pd.DataFrame(json.load(open(E/'retained-log-taxonomy.json')));static=pd.DataFrame(json.load(open(E/'cohort-taxonomy.json')))
 log['log_test_cohort']=log.label.isin(['executed_test_success','test_execution_only']);log['log_assertion_cohort']=log.label.eq('executed_test_success')|log.assertion_only_supported
 log['checkout_equal_head']=log.checkout_comparison.eq('all_observed_checkouts_equal_recorded_head')
 static['static_test_cohort']=static.command_taxonomy.isin(['executed_test_success','test_execution_only'])
 pd.DataFrame(log).to_csv(D/'frozen-log-membership.csv',index=False)
 frozen={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [E/'retained-log-taxonomy.json',E/'retained-log-steps.json',E/'cohort-taxonomy.json',E/'exact-evidence-audit-20261117.md',Path(__file__)]+list(D.glob('predictions-*.csv'))};(D/'score-input-hashes.json').write_text(json.dumps(frozen,indent=2))
 views={}
 for regime,x in regimes.items():
  x=x.merge(log[KEYS+['log_test_cohort','log_assertion_cohort','checkout_equal_head']],on=KEYS,how='left',validate='one_to_one').merge(static[KEYS+['static_test_cohort']],on=KEYS,how='left',validate='one_to_one')
  views[regime+'_all']=x
  views[regime+'_complete_jobs']=x[x.complete_jobs.eq(1)]
  if regime=='zero_label':
   for label in ['log_test_cohort','log_assertion_cohort','checkout_equal_head','static_test_cohort']:views[regime+'_'+label]=x[x[label].fillna(False).astype(bool)]
 rng=np.random.default_rng(42);results={};bootmain={}
 for name,x in views.items():
  projectresults={}
  for repo,d in x.groupby('repository',sort=True):
   y=d.build_result.to_numpy();entry={'rows':len(d),'failures':int(y.sum()),'prevalence':float(y.mean()),'history_branch_rows':int(d.history_branch.sum())}
   if len(np.unique(y))<2:entry['infeasible']='both classes required';projectresults[repo]=entry;continue
   pp={k:d[k].to_numpy() for k in ['B0','C1','constant']+(['online_prior'] if name.startswith('online') else [])}
   entry['metrics']={k:score(y,v) for k,v in pp.items()};entry['paired_ap_delta']=entry['metrics']['C1']['ap']-entry['metrics']['B0']['ap'];clusters=list(pd.Series(np.arange(len(d))).groupby(d.group_id.to_numpy()).indices.values());vals=[]
   for _ in range(1000):
    ii=np.concatenate([clusters[i] for i in rng.integers(0,len(clusters),len(clusters))])
    if len(np.unique(y[ii]))<2:continue
    vals.append(average_precision_score(y[ii],pp['C1'][ii])-average_precision_score(y[ii],pp['B0'][ii]))
   entry['paired_commit_bootstrap95']=np.percentile(vals,[2.5,97.5]).tolist() if vals else None;entry['valid_bootstrap_samples']=len(vals);projectresults[repo]=entry
   if name=='zero_label_all':bootmain[repo]=np.array(vals)
  deltas={r:v['paired_ap_delta'] for r,v in projectresults.items() if 'paired_ap_delta' in v};results[name]={'projects':projectresults,'equal_project_macro_ap_delta':float(np.mean(list(deltas.values()))) if deltas else None,'feasible_projects':len(deltas),'interpretation':'primary' if name=='zero_label_all' else 'secondary selected-evidence sensitivity or onboarding; not a replacement for primary'}
 main=results['zero_label_all'];names=sorted(bootmain);vals=[]
 for _ in range(1000):
  pick=rng.integers(0,len(names),len(names));vals.append(np.mean([rng.choice(bootmain[names[i]]) for i in pick]))
 ci=np.percentile(vals,[2.5,97.5]).tolist();delta={r:v['paired_ap_delta'] for r,v in main['projects'].items()};main['exploratory_hierarchical_project_commit95']=ci;main['project_exchangeability_caveat']='Purposive projects and scientific-Python dependencies weaken this interval; not universal-project proof.';main['leave_one_project_out_macro_delta']={r:float(np.mean([v for k,v in delta.items() if k!=r])) for r in names};main['domain_group_deltas']={'Django':delta['django/django'],'aiohttp':delta['aio-libs/aiohttp'],'scientific_python_equal_project_mean':float(np.mean([delta[x] for x in ['numpy/numpy','pandas-dev/pandas','scikit-learn/scikit-learn']]))};main['reporting_margin']=.02
 main['margin_interpretation']='gain exceeds benchmark margin within weak sampled-project assumptions' if ci[0]>.02 else ('evidence of harm within weak sampled-project assumptions' if ci[1]<0 else ('margin-sized gain not supported; upper bound below 0.02' if ci[1]<.02 else 'inconclusive'))
 output={'status':'frozen external evaluation complete','no_target_fitting_selection_calibration_or_thresholds':True,'practical_margin_is_not_economic_utility':True,'target_reference':'recorded API head-change metadata, not exact executed-source features','narrow_endpoint_caveat':'selected small evidence subsets; assertion-summary support is not pure causal ground truth','results':results,'frozen_score_input_hashes':frozen};OUT.write_text(json.dumps(output,indent=2));print(json.dumps({'primary':main,'secondary_macro':{n:v['equal_project_macro_ap_delta'] for n,v in results.items() if n!='zero_label_all'}},indent=2))
if __name__=='__main__':main()
