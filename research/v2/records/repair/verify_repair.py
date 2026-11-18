from pathlib import Path
import importlib.util,pandas as pd,numpy as np,json
R=Path('/tmp/thesis-repair');E=R/'external-results'
spec=importlib.util.spec_from_file_location('strict',E/'repaired/preprocessing/build_research_features_strict.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
start=np.array([0,10,20,30],dtype=np.int64);avail=np.array([20,15,25,40],dtype=np.int64);y=np.array([1,0,1,0])
h=F.strict_group_history(start,avail,y);assert h['prior_runs'].tolist()==[0,0,1,3];assert h['previous_result'][2]==0
for i in range(4):
 q=y.copy();q[i]=1-q[i];a=F.strict_group_history(start,avail,q)
 for k in h:assert np.isclose(h[k][i],a[k][i],equal_nan=True),(i,k)
for aa in [np.array([np.iinfo(np.int64).min,15,25,40]),np.array([-1,15,25,40])]:
 try:F.strict_group_history(start,aa,y);raise AssertionError('Invalid availability accepted')
 except ValueError:pass
source=pd.read_csv(E/'source-manifest.csv');source['run_started_at']=pd.to_datetime(source.run_started_at,utc=True);source['outcome_available_at']=pd.to_datetime(source.outcome_available_at,utc=True)
bounds=json.loads((E/'training-state.json').read_text())['stage_deadlines'];last=None
for stage,bound in bounds.items():
 g=source[source.stage.eq(stage)];deadline=pd.Timestamp(bound);assert g.run_started_at.lt(deadline).all() and g.outcome_available_at.lt(deadline).all()
 if last is not None:assert g.run_started_at.ge(last).all()
 last=deadline
assert source.groupby('group_id').stage.nunique().max()==1
# Quantify changed original feature values and legacy boundary violations.
orig=pd.read_csv(R/'original-repo/data/processed/research_features.csv');orig['outcome_available_at']=orig.updated_at;strict=F.add_strict_history_features(orig)
cols=json.loads((R/'independent-history-audit.json').read_text())['independent_history_field_mismatches'];changed={c:int((~np.isclose(orig[c],strict[c],equal_nan=True)).sum()) for c in cols}
legacy=pd.read_csv(R/'legacy-comparison-v2/legacy-manifest.csv');fixed=pd.read_csv(R/'legacy-comparison-v2/strict-manifest.csv');v={}
for s in ['fit','selection','calibration','threshold']:
 deadline=pd.Timestamp(json.loads((R/'legacy-comparison-v2/results.json').read_text())['protocol']['strict_boundaries'][['fit','selection','calibration','threshold'].index(s)])
 g=legacy[legacy.stage.eq(s)];v[s]={'rows_starting_at_or_after_next_stage':int(pd.to_datetime(g.run_started_at,utc=True).ge(deadline).sum()),'labels_not_available_before_next_stage':int(pd.to_datetime(g.outcome_available_at,utc=True).ge(deadline).sum())}
report={'tests_passed':['equal-time outcome exclusion','current-outcome invariance in all history fields','missing timestamp rejected','before-start availability rejected','all final source stage row and label deadlines','whole-commit no stage crossing'],'original_rows_with_changed_history_by_field':changed,'legacy_stage_timing_violations':v,'strict_purged_rows':int(fixed.stage.eq('purged').sum()),'latest_frozen_input_validation_impact':'zero, all timestamps valid; branch reproduction unchanged'}
(R/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Paired common-test AP sensitivity interval, commit-level resampling.
from sklearn.metrics import average_precision_score
P=R/'legacy-comparison-v2';a=pd.read_csv(P/'legacy-history_legacy-split-test.csv');b=pd.read_csv(P/'strict-history_strict-split-test.csv');keys=['repository','commit_id','run_id','run_attempt'];c=a.merge(b,on=keys,validate='one_to_one',suffixes=('_old','_strict'));assert c.build_result_old.eq(c.build_result_strict).all();groups=list(c.groupby(['repository','commit_id']).indices.values());rng=np.random.default_rng(42);samples=[]
for _ in range(1000):
 ix=np.concatenate([groups[j] for j in rng.integers(0,len(groups),len(groups))]);z=c.iloc[ix]
 if z.build_result_old.nunique()<2:continue
 samples.append(average_precision_score(z.build_result_old,z.probability_strict)-average_precision_score(z.build_result_old,z.probability_old))
result={'paired_ap_change':float(average_precision_score(c.build_result_old,c.probability_strict)-average_precision_score(c.build_result_old,c.probability_old)),'commit_cluster_95_interval':np.percentile(samples,[2.5,97.5]).tolist(),'rows':len(c),'groups':len(groups),'bootstrap_samples':len(samples),'not_causal_or_fresh_confirmation':True};(R/'repair-effect-interval.json').write_text(json.dumps(result,indent=2));print(result)
