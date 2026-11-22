"""Export reviewed fitted parameters, without fit/retraining or version relabeling.

Only the pinned, trusted repository artifact may be inspected. Its sklearn
version warnings are retained as provenance; old-runtime output is diagnostic.
"""
from pathlib import Path
import json,hashlib,warnings,sys
import joblib,numpy as np,sklearn
from sklearn.exceptions import InconsistentVersionWarning
ROOT=Path(__file__).resolve().parents[2];SOURCE=ROOT/'models/saved/research_build_failure_model.joblib';DEST=ROOT/'models/compatible'
def export():
 expected=json.loads((ROOT/'tests/fixtures/legacy-original-sha256.json').read_text())['models/saved/research_build_failure_model.joblib'];source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
 if expected!=source_sha:raise ValueError('Source artifact is not the reviewed frozen file')
 with warnings.catch_warnings(record=True) as caught:
  warnings.simplefilter('always',InconsistentVersionWarning);artifact=joblib.load(SOURCE)
 model=artifact['model'];pipe=model.estimator.estimator;prep=pipe.steps[0][1];forest=pipe.steps[1][1]
 if type(forest).__name__!='RandomForestClassifier' or model.method!='sigmoid' or len(model.calibrated_classifiers_)!=1:raise ValueError('Unsupported source estimator')
 if model.calibrated_classifiers_[0].estimator not in (model.estimator,pipe):raise ValueError('Unexpected calibration estimator reference')
 if forest.n_outputs_!=1 or list(forest.classes_)!=[0,1] or prep.transformer_weights is not None or prep.remainder!='drop':raise ValueError('Unsupported source routing or class schema')
 numeric=prep.transformers_[0];categorical=prep.transformers_[1];imputer=numeric[1].steps[0][1];scale=numeric[1].steps[1][1];cat_imp=categorical[1].steps[0][1];encoder=categorical[1].steps[1][1]
 if encoder.drop_idx_ is not None or encoder._infrequent_enabled or encoder.handle_unknown!='ignore':raise ValueError('Unsupported categorical encoding')
 if not scale.with_mean or not scale.with_std or imputer.strategy!='median' or cat_imp.strategy!='most_frequent':raise ValueError('Unsupported source preprocessing')
 arrays={'statistics':imputer.statistics_,'indicator':imputer.indicator_.features_,'mean':scale.mean_,'scale':scale.scale_};offsets=[0];parts={k:[] for k in ['left','right','feature','thresholds','p1']}
 for estimator in forest.estimators_:
  tree=estimator.tree_
  if not np.allclose(tree.value[:,0,:].sum(axis=1),1,rtol=0,atol=1e-12):raise ValueError('Unsupported non-probability tree values')
  for key,value in [('left',tree.children_left),('right',tree.children_right),('feature',tree.feature),('thresholds',tree.threshold),('p1',tree.value[:,0,1])]:parts[key].append(value.copy())
  offsets.append(offsets[-1]+tree.node_count)
 arrays.update({k:np.concatenate(v) for k,v in parts.items()});arrays['tree_offsets']=np.array(offsets,dtype=np.int64);DEST.mkdir(exist_ok=True);npz=DEST/'legacy_rf_sigmoid_v1.npz';np.savez_compressed(npz,**arrays)
 sigmoid=model.calibrated_classifiers_[0].calibrators[0]
 manifest={'format':'legacy-rf-sigmoid-v1','array_file':npz.name,'array_sha256':hashlib.sha256(npz.read_bytes()).hexdigest(),'source_file':str(SOURCE.relative_to(ROOT)),'source_sha256':source_sha,'source_reported_sklearn':sorted({getattr(w.message,'original_sklearn_version','unknown') for w in caught if isinstance(w.message,InconsistentVersionWarning)}),'export_runtime_sklearn':sklearn.__version__,'method':'Parameter extraction into a non-pickle NumPy inference format. No fitting, calibration changes or version-string editing.','features':artifact['features'],'numeric':list(numeric[2]),'categorical':list(categorical[2]),'categories':[x.tolist() for x in encoder.categories_],'category_fill':cat_imp.statistics_.tolist(),'tree_count':len(forest.estimators_),'max_depth':max(t.tree_.max_depth for t in forest.estimators_),'transformed_features':forest.n_features_in_,'classes':forest.classes_.tolist(),'sigmoid_a':float(sigmoid.a_),'sigmoid_b':float(sigmoid.b_),'threshold':float(artifact['threshold']),'feature_contract':'legacy-prototype-defaults-v1','rights':'Derived from Shukri/original-contributor artifact; not added to the limited MIT grant.','validation_limit':'Numerical equivalence is checked separately against the recorded sklearn 1.9.1 runtime; see docs/legacy-runtime. This does not establish live accuracy.'}
 (DEST/'legacy_rf_sigmoid_v1.json').write_text(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n');print(json.dumps({'source_sha256':source_sha,'array_sha256':manifest['array_sha256'],'tree_count':manifest['tree_count'],'retrained':False}))
if __name__=='__main__':export()
