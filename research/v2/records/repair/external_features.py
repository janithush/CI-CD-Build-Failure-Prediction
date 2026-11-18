"""External feature construction and invariance checks. No external scores."""
from pathlib import Path
import json,sqlite3,importlib.util,hashlib
import numpy as np
import pandas as pd
from improvement_features import add_change_context,C1_COLUMNS
from improvement_inner import BASE,H,KEYS,T,stages,train_branch
R=Path(__file__).resolve().parent;D=R/'external-evaluation';D.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('F',R/'repaired/preprocessing/build_research_features_strict.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


def history(frame,online):
 d=frame.copy().reset_index(drop=True)
 # Withheld outcomes are moved past every prediction, never treated as NaT
 # because the legacy strict builder sorts NaT before timestamps.
 d['outcome_available_at']=pd.to_datetime(d['last_completed_at'],utc=True)
 valid=d.complete_jobs.eq(1)&d.outcome_available_at.notna()&d.outcome_available_at.ge(d.run_started_at)
 if not online:valid[:]=False
 d.loc[~valid,'outcome_available_at']=pd.Timestamp('2262-01-01',tz='UTC')
 d=F.add_strict_history_features(d)
 d['history_rich']=d.workflow_prior_runs.ge(5)
 return add_change_context(d).replace([np.inf,-np.inf],np.nan)


def raw_features():
 with sqlite3.connect(R/'external-pilot/pilot.sqlite3') as c:
  runs,files=F.load_tables(c);allruns=pd.read_sql_query('SELECT repository,run_id,run_attempt,commit_id,run_started_at FROM workflow_runs',c)
 with sqlite3.connect(R/'external-pilot/evidence.sqlite3') as c:
  evidence=pd.read_sql_query('SELECT repository,run_id,run_attempt,expected,returned,all_terminal AS complete_jobs,last_completed_at FROM jobs_complete',c)
 d=runs.merge(F.aggregate_files(files),on=['repository','commit_id'],how='left',validate='many_to_one')
 counts=['dependency_files_changed','test_files_changed','workflow_files_changed','source_files_changed','config_files_changed','file_extension_count','files_added','files_removed','files_renamed']
 d[counts]=d[counts].fillna(0).astype(int)
 d=d.merge(evidence,on=KEYS,how='left',validate='one_to_one')
 d['run_started_at']=pd.to_datetime(d.run_started_at,utc=True)
 d=d.sort_values(['run_started_at']+KEYS,kind='stable').reset_index(drop=True)
 audit=allruns.merge(d[KEYS],on=KEYS,how='left',indicator=True,validate='one_to_one')
 audit['eligibility_reason']=np.where(audit['_merge'].eq('both'),'eligible','commit metadata absent or commit date after run start')
 audit.to_csv(D/'external-membership.csv',index=False)
 return d


def tests(raw):
 out=[];cold=history(raw,False);online=history(raw,True)
 features=[c for c in BASE if c not in H]+C1_COLUMNS+T.CATEGORICAL_FEATURES
 flip=raw.copy();flip['conclusion']=np.where(raw.conclusion.eq('failure'),'success','failure')
 pd.testing.assert_frame_equal(cold[features],history(flip,False)[features]);out.append('zero-label all outcome flips invariant')
 assert cold.workflow_prior_runs.eq(0).all() and cold.repository_prior_runs.eq(0).all();out.append('zero-label complete history reset')
 for repo,sub in raw.groupby('repository'):
  k=min(100,len(sub)-1);anchor=sub.index[k];cutoff=raw.loc[anchor,'run_started_at']
  changed=raw.copy();future=changed.run_started_at.ge(cutoff)
  changed.loc[future,'conclusion']=np.where(changed.loc[future,'conclusion'].eq('failure'),'success','failure')
  cols=BASE+C1_COLUMNS+T.CATEGORICAL_FEATURES
  pd.testing.assert_frame_equal(online.loc[raw.run_started_at.le(cutoff),cols],history(changed,True).loc[raw.run_started_at.le(cutoff),cols])
  # Full-table construction must equal chronological-prefix construction.
  prefix=raw[raw.run_started_at.le(cutoff)].copy().reset_index(drop=True)
  pd.testing.assert_frame_equal(online[raw.run_started_at.le(cutoff)][cols].reset_index(drop=True),history(prefix,True)[cols])
  first=cold[cold.repository.eq(repo)].iloc[0]
  assert first[[c for c in C1_COLUMNS if c.startswith('past_mean')]].isna().all()
 out.extend(['online future/current outcome flip invariant','chronological prefix feature invariance','no pre-boundary change context'])
 # Independent brute-force outcome reconstruction for all 2,500 rows.
 for _,row in online.iterrows():
  previous=raw[raw.repository.eq(row.repository)&raw.workflow_id.eq(row.workflow_id)&raw.complete_jobs.eq(1)].copy()
  tt=pd.to_datetime(previous.last_completed_at,utc=True)
  previous=previous[tt.lt(row.run_started_at)&tt.ge(previous.run_started_at)]
  assert row.workflow_prior_runs==len(previous)
  if len(previous):assert abs(row.workflow_prior_failure_rate-previous.conclusion.eq('failure').mean())<1e-12
 out.append('every online workflow count and failure rate matches independent released-outcome scan')
 # Construct same-timestamp and incomplete evidence edge cases.
 toy=raw.iloc[:3].copy().reset_index(drop=True);toy['repository']='synthetic';toy['workflow_id']=1;toy['branch']='main';toy['commit_id']=['a','b','c'];toy['run_started_at']=pd.to_datetime(['2026-01-01T00:00Z','2026-01-01T01:00Z','2026-01-01T02:00Z']);toy['last_completed_at']=['2026-01-01T01:00Z','2026-01-01T01:30Z','2026-01-01T03:00Z'];toy['complete_jobs']=[1,0,1]
 q=history(toy,True);assert list(q.workflow_prior_runs)==[0,0,1];out.append('equal-time completion and incomplete outcomes excluded')
 report={'status':'passed','checks':out,'rows':len(raw),'projects':raw.repository.nunique(),'cold_route_counts':cold.groupby('repository').history_rich.value_counts().to_dict().__str__(),'online_routes':online.groupby(['repository','history_rich']).size().to_dict().__str__(),'performance_scored':False}
 (D/'feature-tests.json').write_text(json.dumps(report,indent=2));cold.to_csv(D/'features-zero-label.csv',index=False);online.to_csv(D/'features-online.csv',index=False);print(json.dumps(report,indent=2),flush=True)
 return cold,online


def fit():
 source=pd.read_csv(R/'five_features_improvement.csv',dtype={'workflow_id':'string'})
 for c in ['run_started_at','outcome_available_at']:source[c]=pd.to_datetime(source[c],utc=True)
 end=pd.Timestamp('2026-07-01',tz='UTC');source=source[source.run_started_at.lt(end)].copy();source['group_id']=source.repository+'::'+source.commit_id
 source,bounds=stages(source,end);source[KEYS+['commit_id','group_id','run_started_at','outcome_available_at','stage']].to_csv(D/'source-manifest.csv',index=False)
 # Only source rows are supplied for model serialization predictions. No target scores or labels used.
 dummy=source[source.stage.eq('threshold')].iloc[:10].copy()
 configs={'B0-history':BASE,'B0-no-history':[c for c in BASE if c not in H],'C1-history':BASE+C1_COLUMNS,'C1-no-history':[c for c in BASE if c not in H]+C1_COLUMNS}
 result={'stage_deadlines':bounds,'branches':{},'constant_prevalence':float(source[source.stage.eq('fit')].build_result.mean()),'external_scores_computed':False}
 for name,cols in configs.items():
  print('Fitting',name,flush=True);result['branches'][name],_=train_branch(source,dummy,cols,D/name)
  (D/'training-state.json').write_text(json.dumps(result,indent=2))
 manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'five_features_improvement.csv',R/'external-pilot/frozen-external-design-20261117.md',Path(__file__)]+sorted(D.glob('*.joblib'))+sorted(D.glob('features-*.csv'))}
 (D/'pre-score-hashes.json').write_text(json.dumps(manifest,indent=2));print('SOURCE TRAINING COMPLETE',flush=True)

if __name__=='__main__':
 import sys
 if '--fit' in sys.argv:fit()
 else:tests(raw_features())
