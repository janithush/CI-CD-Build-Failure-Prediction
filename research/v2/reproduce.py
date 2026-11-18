"""Verify frozen results, replay saved models, or refit source-only extended branches.

No network requests, collection, API triggers or deployment happen here.
"""
from pathlib import Path
import argparse,json,hashlib,sys
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score,brier_score_loss,confusion_matrix

ROOT=Path(__file__).resolve().parent
KEYS=['repository','run_id','run_attempt']
REGIMES={'original5-zero':'original5-zero-static','later4-zero':'later4-zero-static','original5-online':'original5-online-history'}

def frame(name):
    return pd.read_csv(ROOT/'data'/(name+'.csv.gz'),dtype={'workflow_id':'string'})

def verify():
    rows=[]
    for regime in REGIMES:
        d=frame(regime+'-predictions')
        assert not d.duplicated(KEYS).any()
        for repo,g in d.groupby('repository'):
            y=g.build_result
            for name in ['B0','C1','extended']:
                p=g[name];tn,fp,fn,tp=confusion_matrix(y,p>=g[name+'_threshold'],labels=[0,1]).ravel()
                rows.append({'regime':regime,'repository':repo,'model':name,'AP':average_precision_score(y,p),'Brier':brier_score_loss(y,p),'TP':tp,'FP':fp,'TN':tn,'FN':fn,'warning_rate':(tp+fp)/len(g),'false_alarms_per_100_runs':100*fp/len(g)})
    result=pd.DataFrame(rows);saved=pd.read_csv(ROOT/'results/metrics-by-project.csv');keys=['regime','repository','model'];merged=result.merge(saved,on=keys,validate='one_to_one',suffixes=('_new','_saved'))
    for col in ['AP','Brier','TP','FP','TN','FN','warning_rate','false_alarms_per_100_runs']:
        assert np.allclose(merged[col+'_new'],merged[col+'_saved'],rtol=0,atol=1e-12),col
    macro=result.groupby(['regime','model'])[['AP','Brier','warning_rate','false_alarms_per_100_runs']].mean()
    expected=pd.read_csv(ROOT/'results/macro-before-after.csv').set_index(['regime','model'])
    pd.testing.assert_frame_equal(macro.sort_index(),expected[macro.columns].sort_index(),atol=1e-12,rtol=0)
    print(f'PASS: {len(result)} project/model/regime rows; AP, Brier, confusion counts and macro means match.')
    print(macro.to_string())
    return result

def replay():
    import joblib
    for regime,features in REGIMES.items():
        d=frame(features);expected=frame(regime+'-predictions');assert d[KEYS].astype(str).equals(expected[KEYS].astype(str))
        for name in ['B0','C1','extended']:
            stem='extended' if name=='extended' else name
            nh=joblib.load(ROOT/'models'/(stem+'-no-history.joblib'))
            p=nh['model'].predict_proba(d[nh['features']])[:,1]
            if regime.endswith('online'):
                hist=joblib.load(ROOT/'models'/(stem+'-history.joblib'))
                hp=hist['model'].predict_proba(d[hist['features']])[:,1]
                p=np.where(d.history_rich,hp,p)
            delta=float(np.max(np.abs(p-expected[name])))
            assert delta<1e-12,(regime,name,delta)
            print('PASS saved model replay:',regime,name,'maximum absolute difference',delta)

def refit(output):
    sys.path.insert(0,str(ROOT/'src'))
    from improvement_inner import stages,train_branch,BASE,H,T
    from improvement_features import C1_COLUMNS
    contract=json.load(open(ROOT/'results/feature-contract.json'))
    d=frame('source-history')
    for c in ['run_started_at','outcome_available_at']:d[c]=pd.to_datetime(d[c],utc=True)
    cut=pd.Timestamp('2026-07-01',tz='UTC');d=d[d.run_started_at.lt(cut)].copy();d['group_id']=d.repository+'::'+d.commit_id
    d,bounds=stages(d,cut);counts=d.stage.value_counts().to_dict()
    for name,n in [('fit',7073),('selection',1273),('calibration',1159),('threshold',1222)]:assert counts[name]==n
    # A new output directory is mandatory so this never overwrites frozen results.
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    (output/'bounds.json').write_text(json.dumps(bounds,indent=2))
    configs={'extended-no-history':[c for c in BASE if c not in H]+C1_COLUMNS+contract['static'],'extended-history':BASE+C1_COLUMNS+contract['static']+contract['history']}
    original=T.candidates
    def bounded(weight):
        models=original(weight)
        for model in models.values():
            if 'n_jobs' in model.get_params():model.set_params(n_jobs=2)
        return models
    T.candidates=bounded
    for name,features in configs.items():
        result,_=train_branch(d,d[d.stage.eq('threshold')].iloc[:10].copy(),features,output/name)
        frozen=json.load(open(ROOT/'models'/(name+'.json')))
        assert result['selected_model']==frozen['selected_model']
        assert result['source_threshold']==frozen['source_threshold']
        print('PASS source-only refit:',name,result['selected_model'],result['source_threshold'])
    print('Refit outputs:',output)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['verify','replay','refit']);p.add_argument('--output',default='research-v2-refit');a=p.parse_args()
    if a.mode=='verify':verify()
    elif a.mode=='replay':replay()
    else:refit(a.output)
