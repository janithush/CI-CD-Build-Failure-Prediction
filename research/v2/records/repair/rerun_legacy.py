from pathlib import Path
import importlib.util,sys,json,hashlib,shutil,numpy as np,pandas as pd
ROOT=Path('/tmp/thesis-repair');E=ROOT/'external-results';sys.path.insert(0,str(E))
from improvement_inner import BASE,T
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score
import joblib
def train_branch(source,target,features,dest):
 parts={n:source[source.stage.eq(n)] for n in ['fit','selection','calibration','threshold']}
 T.NUMERIC_FEATURES=list(features);cols=list(features)+T.CATEGORICAL_FEATURES;fit=parts['fit'];scores={};models={}
 for name,clf in T.candidates(fit.build_result.eq(0).sum()/fit.build_result.eq(1).sum()).items():
  if name=='dummy_prior':continue
  model=Pipeline([('preprocess',T.preprocessor()),('classifier',clf)]);model.fit(fit[cols],fit.build_result);scores[name]=float(average_precision_score(parts['selection'].build_result,model.predict_proba(parts['selection'][cols])[:,1]));models[name]=model
 best=max(scores,key=scores.get);model=CalibratedClassifierCV(FrozenEstimator(models[best]),method='sigmoid');model.fit(parts['calibration'][cols],parts['calibration'].build_result);thr=T.best_f1_threshold(parts['threshold'].build_result,model.predict_proba(parts['threshold'][cols])[:,1]);p=model.predict_proba(target[cols])[:,1]
 result={'selected_model':best,'selection_ap':scores,'source_threshold':thr,'source_stages':{n:{'rows':len(g),'failures':int(g.build_result.sum())} for n,g in parts.items()}}
 dest.with_suffix('.json').write_text(json.dumps(result,indent=2));joblib.dump({'model':model,'features':cols,'source_threshold':thr},dest.with_suffix('.joblib'),compress=3);return result,p
spec=importlib.util.spec_from_file_location('strict',E/'repaired/preprocessing/build_research_features_strict.py');F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)
# Limit parallel execution only, retaining estimators, seeds and settings.
original_candidates=T.candidates
def bounded(weight):
 r=original_candidates(weight)
 for model in r.values():
  if 'n_jobs' in model.get_params():model.set_params(n_jobs=2)
 return r
T.candidates=bounded
R=ROOT/'original-repo';O=ROOT/'legacy-comparison-v2';O.mkdir(exist_ok=True)
d=pd.read_csv(R/'data/processed/research_features.csv',dtype={'workflow_id':'string'})
for c in ['run_started_at','updated_at']:d[c]=pd.to_datetime(d[c],utc=True)
d['outcome_available_at']=d.updated_at
assert d.outcome_available_at.notna().all() and d.outcome_available_at.ge(d.run_started_at).all()
m=pd.read_csv(R/'data/processed/research_split_manifest.csv');keys=['repository','commit_id','run_id','run_attempt'];d=d.merge(m,on=keys,validate='one_to_one').sort_values('run_started_at').reset_index(drop=True)
v=d[d.split.eq('validation')];third=len(v)//3
legacy=d.copy();legacy['stage']='test';legacy.loc[legacy.split.eq('train'),'stage']='fit'
legacy.loc[v.index[:third],'stage']='selection';legacy.loc[v.index[third:2*third],'stage']='calibration';legacy.loc[v.index[2*third:],'stage']='threshold'
bounds=[legacy.loc[legacy.stage.eq(s),'run_started_at'].min() for s in ['selection','calibration','threshold','test']]
strict=F.add_strict_history_features(d.copy());strict['stage']='purged';names=['fit','selection','calibration','threshold','test']
for group,g in strict.groupby('group_id'):
 lo=g.run_started_at.min();hi=g.run_started_at.max();k=sum(lo>=b for b in bounds)
 if k==4 or (hi<bounds[k] and g.outcome_available_at.lt(bounds[k]).all()):strict.loc[g.index,'stage']=names[k]
strict[keys+['group_id','run_started_at','outcome_available_at','stage']].to_csv(O/'strict-manifest.csv',index=False)
legacy[keys+['group_id','run_started_at','outcome_available_at','stage']].to_csv(O/'legacy-manifest.csv',index=False)
# Crossed histories/splits measure both repair effects, not a new model search.
reports={};predictions={}
for hist,split in [('legacy','legacy'),('strict','legacy'),('legacy','strict'),('strict','strict')]:
 frame=(strict if hist=='strict' else legacy).copy();frame['stage']=(strict if split=='strict' else legacy).stage
 tag=hist+'-history_'+split+'-split';target=frame[frame.stage.eq('test')].copy();source=frame[~frame.stage.eq('test')].copy()
 print('START',tag,source.groupby('stage').size().to_dict(),len(target),flush=True)
 metadata,p=train_branch(source,target,BASE,O/tag)
 metrics=T.metric_values(target.build_result,p,metadata['source_threshold']);reports[tag]={'model':metadata['selected_model'],'source_stages':metadata['source_stages'],'metrics':metrics}
 prediction=target[keys+['build_result','run_started_at']].assign(probability=p);prediction.to_csv(O/(tag+'-test.csv'),index=False);predictions[tag]=prediction
 (O/'results.json').write_text(json.dumps(reports,indent=2));print('DONE',tag,metrics,flush=True)
common=predictions['legacy-history_legacy-split'][keys].merge(predictions['strict-history_strict-split'][keys],on=keys)
for tag,p in predictions.items():
 c=common.merge(p,on=keys,validate='one_to_one');reports[tag]['common_test_metrics']=T.metric_values(c.build_result,c.probability.to_numpy(),json.loads((O/(tag+'.json')).read_text())['source_threshold'])
reports['protocol']={'original_commit':'6cd82763bafc1657501c2df8df39996b273e7e63','rows':len(d),'strict_boundaries':[str(b) for b in bounds],'common_test_rows':len(common),'purpose':'retrospective repair sensitivity, not independent confirmation','availability':'recorded updated_at unchanged','model_settings':'same original six fixed candidates and seeds; n_jobs=2 only','legacy_published_metrics':json.loads((R/'reports/research_model_results.json').read_text())['test_metrics']}
(O/'results.json').write_text(json.dumps(reports,indent=2));print('COMPLETE',flush=True)
