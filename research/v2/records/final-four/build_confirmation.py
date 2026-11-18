from pathlib import Path
import sys,sqlite3,json,hashlib
import pandas as pd,numpy as np
R=Path('/tmp/thesis-final-four');E=Path('/tmp/thesis-repair/external-results');C=R/'confirmation';sys.path.insert(0,str(E))
from external_features import F,history,BASE,H,T,C1_COLUMNS
assert not (C/'RESULTS.json').exists(),'Confirmation scores already exist; do not rewrite features after scoring'
with sqlite3.connect(C/'cohort.sqlite3') as db:
 raw,files=F.load_tables(db);allruns=pd.read_sql_query('SELECT repository,run_id,run_attempt,commit_id,run_started_at FROM workflow_runs',db)
raw=raw.merge(F.aggregate_files(files),on=['repository','commit_id'],how='left',validate='many_to_one')
counts=['dependency_files_changed','test_files_changed','workflow_files_changed','source_files_changed','config_files_changed','file_extension_count','files_added','files_removed','files_renamed'];raw[counts]=raw[counts].fillna(0).astype(int)
raw['run_started_at']=pd.to_datetime(raw.run_started_at,utc=True);raw=raw[pd.to_datetime(raw.commit_date,utc=True).notna()&pd.to_datetime(raw.commit_date,utc=True).le(raw.run_started_at)&raw.files_changed.lt(3000)].sort_values(['run_started_at','repository','run_id','run_attempt'],kind='stable').reset_index(drop=True)
raw['complete_jobs']=0;raw['last_completed_at']=pd.NaT
x=history(raw,False);x['workflow_id']=x.workflow_id.astype('string');cols=[c for c in BASE if c not in H]+C1_COLUMNS+T.CATEGORICAL_FEATURES
flip=raw.copy();flip['conclusion']=np.where(flip.conclusion.eq('success'),'failure','success');q=history(flip,False);q['workflow_id']=q.workflow_id.astype('string');pd.testing.assert_frame_equal(x[cols],q[cols]);assert x.workflow_prior_runs.eq(0).all()
for repo,g in raw.groupby('repository'):
 if len(g)<3:continue
 cutoff=g.run_started_at.iloc[len(g)//2];prefix=raw[raw.run_started_at.le(cutoff)].copy().reset_index(drop=True);q=history(prefix,False);q['workflow_id']=q.workflow_id.astype('string');pd.testing.assert_frame_equal(x[raw.run_started_at.le(cutoff)][cols].reset_index(drop=True),q[cols])
keys=['repository','run_id','run_attempt'];membership=allruns.merge(x[keys],on=keys,how='left',indicator=True);membership['feature_eligibility']=np.where(membership['_merge'].eq('both'),'eligible','missing/future commit metadata or >=3000-file API truncation risk');membership.to_csv(C/'frozen-membership.csv',index=False);x.to_csv(C/'frozen-features.csv',index=False)
coverage=x.groupby('repository').agg(rows=('run_id','size'),failures=('build_result','sum'));coverage['qualifies']=coverage.rows.ge(200);coverage.to_csv(C/'coverage.csv');assert coverage.qualifies.sum()>=3
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'PROTOCOL.md',R/'ROSTER_AMENDMENT.md',R/'freeze-hashes.json',C/'frozen-features.csv',C/'frozen-membership.csv',Path(__file__)]+list(Path('/tmp/thesis-repair/final-reproduction').glob('*-no-history.joblib'))};(C/'pre-score-hashes.json').write_text(json.dumps(hashes,indent=2));(C/'FEATURE_CHECKS.json').write_text(json.dumps({'outcome_flip_invariance':'passed','zero_outcome_history':'passed','chronological_prefix_invariance':'passed','coverage':coverage.reset_index().to_dict('records'),'scores_exposed':False},indent=2));print(coverage.to_string())
