import unittest,tempfile,json,hashlib,shutil,subprocess,sys,importlib,warnings
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd,joblib
from fastapi.testclient import TestClient
from sklearn.exceptions import InconsistentVersionWarning
from api.portable_legacy import PortableLegacy
from api import risk_analyzer as risk,prediction_store as store
from api.main import app
from api import main as main_api
ROOT=Path(__file__).resolve().parents[1];MANIFEST=ROOT/'models/compatible/legacy_rf_sigmoid_v1.json'
class PortableLegacyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.database=patch.object(store,'DATABASE_PATH',Path(self.temp.name)/'records.sqlite3');self.database.start();self.legacy_database=patch.object(main_api,'DATABASE_PATH',Path(self.temp.name)/'records.sqlite3');self.legacy_database.start();main_api.init_history_db()
 def tearDown(self):self.legacy_database.stop();self.database.stop();self.temp.cleanup()
 def frame(self):return risk.build_research_features(json.loads((ROOT/'tests/fixtures/combined/public-repository-connection.json').read_text())['commit_analysis'])
 def test_original_and_existing_artifacts_unchanged_from_frozen_release(self):
  for path in ['models/saved/research_build_failure_model.joblib','models/saved/best_build_failure_model.pkl','models/saved/build_failure_model.pkl']:
   expected=hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','v2.0.0:'+path])).hexdigest();self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),expected)
 def test_no_original_pickle_load_during_serving(self):
  with patch.object(joblib,'load',side_effect=AssertionError('No pickle allowed in serving')):
   with warnings.catch_warnings(record=True) as caught:
    importlib.reload(risk);self.assertFalse(risk._runtime_mismatches);p=risk.predict_build_risk(self.frame().iloc[0].to_dict())
   self.assertFalse(any(isinstance(w.message,InconsistentVersionWarning) for w in caught));self.assertEqual(p['model_info']['serving_format'],'legacy-rf-sigmoid-v1')
 def test_source_diagnostic_probability_parity(self):
  with warnings.catch_warnings():warnings.simplefilter('ignore',InconsistentVersionWarning);original=joblib.load(ROOT/'models/saved/research_build_failure_model.joblib')['model']
  frame=pd.read_csv(ROOT/'data/processed/research_features.csv',dtype={'workflow_id':str}).sample(n=512,random_state=17);portable=PortableLegacy(MANIFEST);np.testing.assert_allclose(portable.predict_proba(frame),original.predict_proba(frame),atol=1e-12,rtol=0)
 def test_unknown_categories_missing_values_and_invalid_inputs(self):
  m=PortableLegacy(MANIFEST);frame=self.frame()
  for name in m.categorical:frame[name]='unseen-controlled'
  frame.loc[0,m.numeric[0]]=np.nan;self.assertTrue(np.isfinite(m.predict_proba(frame)).all())
  with self.assertRaises(ValueError):m.predict_proba(frame.drop(columns=[m.features[0]]))
  frame.loc[0,m.numeric[1]]=np.inf
  with self.assertRaises(ValueError):m.predict_proba(frame)
 def test_array_and_manifest_corruption_fail_closed(self):
  folder=Path(self.temp.name);data=json.loads(MANIFEST.read_text());shutil.copy(MANIFEST,folder/MANIFEST.name);shutil.copy(MANIFEST.with_name(data['array_file']),folder/data['array_file'])
  p=folder/data['array_file'];p.write_bytes(p.read_bytes()+b'controlled-corruption')
  with self.assertRaisesRegex(ValueError,'integrity'):PortableLegacy(folder/MANIFEST.name)
  (folder/MANIFEST.name).write_text('{}')
  with self.assertRaisesRegex(ValueError,'reviewed'):PortableLegacy(folder/MANIFEST.name)
 def test_export_is_reproducible_and_does_not_retrain(self):
  paths=[MANIFEST,MANIFEST.with_suffix('.npz')];before=[p.read_bytes() for p in paths]
  subprocess.run([sys.executable,str(ROOT/'tools/model_compat/export_legacy.py')],cwd=ROOT,check=True,capture_output=True)
  self.assertEqual(before,[p.read_bytes() for p in paths]);self.assertIn('No fitting',json.loads(MANIFEST.read_text())['method'])
 def test_full_portable_output_against_saved_genuine_191_reference(self):
  from tools.model_compat.validate_legacy import validate
  result=validate(portable_only_reference=ROOT/'tests/fixtures/legacy_reference_191.npz')
  self.assertTrue(result['recorded_version_reference']);self.assertEqual(result['source_threshold_disagreements'],0);self.assertEqual(result['stress_threshold_disagreements'],0)
 def test_api_refuses_failed_portable_startup_without_fallback(self):
  try:
   with patch('api.portable_legacy.PortableLegacy',side_effect=ValueError('Controlled invalid artifact')):
    importlib.reload(risk);client=TestClient(app);payload=json.loads((ROOT/'tests/fixtures/combined/public-repository-connection.json').read_text())['commit_analysis'];self.assertFalse(client.get('/health').json()['legacy_inference_available']);self.assertEqual(client.post('/predict-connected-repo',json=payload).status_code,503)
  finally:importlib.reload(risk)
 def test_independent_toy_forest_average_split_and_sigmoid(self):
  m=PortableLegacy(MANIFEST);m.manifest=dict(m.manifest,max_depth=1,sigmoid_a=-2.,sigmoid_b=.3)
  # Two stump families, not the source model, give an analytical result.
  m.arrays={'tree_offsets':np.arange(301)*3,'left':np.tile([1,-1,-1],300),'right':np.tile([2,-1,-1],300),'feature':np.tile([0,-2,-2],300),'thresholds':np.tile([.5,-2,-2],300),'p1':np.concatenate([np.tile([0,.2,.8],200),np.tile([0,.4,.6],100)])}
  raw=np.array([(.2*200+.4*100)/300,(.8*200+.6*100)/300]);expected=1/(1+np.exp(-2*raw+.3))
  with patch.object(m,'transform',return_value=np.array([[.5],[.5001]],dtype=np.float32)):
   result=m.predict_proba(pd.DataFrame(index=[0,1]));np.testing.assert_allclose(result[:,1],expected,atol=1e-14,rtol=0);np.testing.assert_allclose(result.sum(axis=1),1,atol=0,rtol=0)
 def test_api_restored_prediction_has_bound_record_and_separate_advice(self):
  payload=json.loads((ROOT/'tests/fixtures/combined/public-repository-connection.json').read_text())['commit_analysis'];client=TestClient(app);response=client.post('/predict-connected-repo',json=payload);self.assertEqual(response.status_code,200,response.text);p=response.json()['prediction'];record=p['record']
  self.assertAlmostEqual(record['raw_probability']*100,p['raw_model_probability'],places=12);self.assertEqual(record['advisory_risk_score'],p['advisory_risk_score']);self.assertEqual(record['model_sha256'],p['model_info']['artifact_sha256']);self.assertEqual(record['feature_contract'],'legacy-prototype-defaults-v1')
  self.assertEqual(store.get(record['prediction_id'],payload['repository']),record);self.assertEqual(client.post('/research/feedback',json={'prediction_id':record['prediction_id'],'repository':payload['repository'],'assessment':'helpful'}).status_code,200)
  self.assertTrue(client.get('/health').json()['legacy_inference_available'])
if __name__=='__main__':unittest.main()
