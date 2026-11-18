"""Source-only nested selection. Drops the outer project before splitting, fitting or scoring.
Usage: python improvement_inner.py OUTER_REPO INNER_REPO
One resumable job per source-inner fold. All tried models/results are retained.
"""
from pathlib import Path
import sys, json, importlib.util, hashlib, time, joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score
from improvement_features import C1_COLUMNS, C2_COLUMNS, history_rich_mask

R = Path(__file__).resolve().parent
O = R/'improvement-results'/'inner'; O.mkdir(parents=True,exist_ok=True)
spec = importlib.util.spec_from_file_location('trainer', R/'trainer.py')
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
BASE = list(T.NUMERIC_FEATURES)
H = ['workflow_prior_runs','repository_prior_runs','previous_workflow_result','workflow_prior_failure_rate','repository_prior_failure_rate','branch_prior_failure_rate','workflow_failure_rate_3','workflow_failure_rate_5','workflow_failure_rate_10','workflow_failure_rate_20','hours_since_previous_workflow_run','hours_since_previous_failure']
KEYS = ['repository','run_id','run_attempt']
INNER = pd.Timestamp('2026-04-01', tz='UTC')
END = pd.Timestamp('2026-07-01', tz='UTC')


def stages(source, end):
    source = source.copy()
    g = source.groupby('group_id').run_started_at.agg(['min','max']).sort_values('min',kind='stable')
    if len(g)<20: raise ValueError('too few commit groups')
    bounds = [g.iloc[int(len(g)*x)]['min'] for x in [.7,.8,.9]]+[end]
    names = ['fit','selection','calibration','threshold']
    latest = source.groupby('group_id').outcome_available_at.max()
    missing = source.groupby('group_id').outcome_available_at.apply(lambda x:x.isna().any())
    mapping = {}
    for group,row in g.iterrows():
        i = sum(row['min']>=b for b in bounds[:-1])
        valid = row['max']<bounds[i] and not missing[group] and latest[group]<bounds[i]
        mapping[group] = names[i] if valid else 'purged'
    source['stage'] = source.group_id.map(mapping)
    for i,name in enumerate(names):
        part=source[source.stage.eq(name)]
        assert part.run_started_at.lt(bounds[i]).all()
        assert part.outcome_available_at.notna().all() and part.outcome_available_at.lt(bounds[i]).all()
    return source, {name:str(b) for name,b in zip(names,bounds)}


def train_branch(source, target, features, dest):
    """Fixed original six models, source-only selection and sigmoid calibration."""
    model_path = dest.with_suffix('.json')
    prediction_path = dest.with_suffix('.csv')
    if model_path.exists() and prediction_path.exists():
        result=json.loads(model_path.read_text())
        p=pd.read_csv(prediction_path)
        assert p[KEYS].astype(str).equals(target[KEYS].reset_index(drop=True).astype(str))
        return result,p.probability.to_numpy()
    parts={n:source[source.stage.eq(n)].sort_values('run_started_at') for n in ['fit','selection','calibration','threshold']}
    counts={n:{'rows':len(d),'failures':int(d.build_result.sum())} for n,d in parts.items()}
    if any(len(d)<10 or d.build_result.nunique()<2 for d in parts.values()):
        raise ValueError('infeasible branch stages: '+json.dumps(counts))
    T.NUMERIC_FEATURES=list(features)
    cols=T.NUMERIC_FEATURES+T.CATEGORICAL_FEATURES
    fit=parts['fit']; select=parts['selection']; cal=parts['calibration']; threshold=parts['threshold']
    weight=fit.build_result.eq(0).sum()/fit.build_result.eq(1).sum()
    scores={}; models={}
    for name,clf in T.candidates(weight).items():
        if name=='dummy_prior':continue
        p=Pipeline([('preprocess',T.preprocessor()),('classifier',clf)])
        p.fit(fit[cols],fit.build_result)
        scores[name]=float(average_precision_score(select.build_result,p.predict_proba(select[cols])[:,1]));models[name]=p
    best=max(scores,key=scores.get)
    model=CalibratedClassifierCV(FrozenEstimator(models[best]),method='sigmoid')
    model.fit(cal[cols],cal.build_result)
    thr=T.best_f1_threshold(threshold.build_result,model.predict_proba(threshold[cols])[:,1])
    p=model.predict_proba(target[cols])[:,1]
    result={'selected_model':best,'selection_ap':scores,'features':cols,'source_stages':counts,'source_threshold':float(thr)}
    joblib.dump({'model':model,'features':cols,'source_threshold':float(thr)},dest.with_suffix('.joblib'),compress=3)
    target[KEYS].assign(probability=p).to_csv(prediction_path,index=False)
    model_path.write_text(json.dumps(result,indent=2))
    return result,p


def main(outer,inner):
    start=time.monotonic()
    if outer==inner:raise ValueError('outer and inner must differ')
    name=outer.replace('/','_')+'__'+inner.replace('/','_'); directory=O/name;directory.mkdir(exist_ok=True)
    resultpath=directory/'results.json'
    if resultpath.exists():print('already complete',resultpath);return
    d=pd.read_csv(R/'five_features_improvement.csv',dtype={'workflow_id':'string'})
    d=d[d.repository.ne(outer)].copy() # Drop outer before any split, fit, scoring or selection.
    for col in ['run_started_at','outcome_available_at']:d[col]=pd.to_datetime(d[col],utc=True)
    assert not d.repository.eq(outer).any()
    d['group_id']=d.repository+'::'+d.commit_id
    source=d[d.repository.ne(inner)&d.run_started_at.lt(INNER)].copy()
    target=d[d.repository.eq(inner)&d.run_started_at.ge(INNER)&d.run_started_at.lt(END)&d.outcome_available_at.lt(END)].sort_values(['run_started_at','run_id','run_attempt'],kind='stable').copy()
    assert source.repository.nunique()==3
    source,bounds=stages(source,INNER)
    source[KEYS+['commit_id','group_id','run_started_at','outcome_available_at','stage']].to_csv(directory/'source-manifest.csv',index=False)
    target[KEYS+['commit_id','group_id','run_started_at','outcome_available_at','build_result']].to_csv(directory/'validation-manifest.csv',index=False)
    if len(target)<10 or target.build_result.nunique()<2:
        resultpath.write_text(json.dumps({'feasible':False,'reason':'inner validation class support','rows':len(target),'outer':outer,'inner':inner},indent=2));return
    configs={'B0':BASE,'C1':BASE+C1_COLUMNS,'NH':[c for c in BASE if c not in H],'C1_NH':[c for c in BASE if c not in H]+C1_COLUMNS,'C2':BASE+C2_COLUMNS,'C1_C2':BASE+C1_COLUMNS+C2_COLUMNS}
    branches={}; metadata={}
    try:
        for name,features in configs.items():
            print(outer,inner,'branch',name,flush=True)
            metadata[name],branches[name]=train_branch(source,target,features,directory/('branch-'+name))
    except ValueError as e:
        resultpath.write_text(json.dumps({'feasible':False,'reason':str(e),'outer':outer,'inner':inner,'completed_branches':list(branches)},indent=2));return
    rich=history_rich_mask(target)
    predictions={'B0':branches['B0'],'C1':branches['C1'],'C3':np.where(rich,branches['B0'],branches['NH']),'C1+C3':np.where(rich,branches['C1'],branches['C1_NH']),'C2':branches['C2'],'C1+C3+C2':np.where(rich,branches['C1_C2'],branches['C1_NH'])}
    prevalence=float(target.build_result.mean())
    scores={n:{'ap':float(average_precision_score(target.build_result,p)),'ap_minus_prevalence':float(average_precision_score(target.build_result,p)-prevalence)} for n,p in predictions.items()}
    output={'feature_input_sha256':hashlib.sha256((R/'five_features_improvement.csv').read_bytes()).hexdigest(),'outer':outer,'inner':inner,'feasible':True,'inner_cutoff':str(INNER),'validation_end':str(END),'validation_rows':len(target),'validation_prevalence':prevalence,'stage_deadlines':bounds,'candidate_metrics':scores,'branch_models':metadata,'route_counts':{str(k):{'rows':int((rich==k).sum()),'failures':int(target.loc[rich==k,'build_result'].sum())} for k in [False,True]},'seconds':time.monotonic()-start}
    target[KEYS+['commit_id','group_id','run_started_at','build_result']].assign(history_rich=rich,**predictions).to_csv(directory/'paired-predictions.csv',index=False)
    resultpath.write_text(json.dumps(output,indent=2));print('done',outer,inner,scores,flush=True)

if __name__=='__main__':main(*sys.argv[1:])
