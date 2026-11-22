import unittest,tempfile,json,sqlite3
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import prediction_store as store, research_service as service
from api.main import app

class PredictionStoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.patch=patch.object(store,'DATABASE_PATH',Path(self.temp.name)/'records.sqlite3');self.patch.start();self.client=TestClient(app)
 def tearDown(self):self.patch.stop();self.temp.cleanup()
 def record(self):
  row=service.frozen_frame('original5-zero').iloc[0]
  return self.client.post('/research/replay',json={'regime':'original5-zero','repository':row.repository,'run_id':int(row.run_id),'run_attempt':int(row.run_attempt),'model':'C1'}).json()
 def test_provenance_record_exact_and_isolated(self):
  x=self.record();self.assertEqual(len(x['prediction_id']),32);self.assertEqual(len(x['input_sha256']),64);self.assertTrue(x['features']);self.assertIsNone(x['advisory_risk_score']);self.assertEqual(x['raw_probability_units'],'fraction-0-to-1')
  self.assertEqual(self.client.get('/research/history',params={'repository':x['repository']}).json()['history'][0],x)
  self.assertEqual(self.client.get('/research/history',params={'repository':'other/project'}).json()['history'],[])
  self.assertEqual(self.client.get('/research/predictions/'+x['prediction_id'],params={'repository':'other/project'}).status_code,404)
  self.assertEqual(self.client.get('/research/history').status_code,422)
 def test_feedback_binds_prediction_and_does_not_train(self):
  x=self.record();body={'prediction_id':x['prediction_id'],'repository':x['repository'],'assessment':'helpful'}
  response=self.client.post('/research/feedback',json=body);self.assertEqual(response.status_code,200,response.text);self.assertIn('No verified CI outcome',response.json()['learning_status'])
  self.assertEqual(store.get(x['prediction_id'],x['repository']),x)
  body['repository']='other/project';self.assertEqual(self.client.post('/research/feedback',json=body).status_code,404)
  body['github_token']='controlled-not-a-real-secret';self.assertEqual(self.client.post('/research/feedback',json=body).status_code,422)
 def test_store_whitelist_drops_credentials_and_logs(self):
  x=self.record();x.update(github_token='controlled-not-a-real-secret',previous_error_message='controlled-log',password='not-real');saved=store.save(x)
  for k in ['github_token','previous_error_message','password']:self.assertNotIn(k,saved)
  self.assertNotIn('controlled-not-a-real-secret',store.DATABASE_PATH.read_bytes().decode(errors='ignore'))
 def test_nonlocal_clients_and_origins_blocked(self):
  for origin in ['https://evil.example','null','http://127.0.0.1.evil.example']:
   self.assertEqual(self.client.get('/research/status',headers={'Origin':origin}).status_code,403)
  self.assertEqual(self.client.get('/research/status',headers={'Origin':'http://localhost:8080'}).status_code,200)
  with TestClient(app,client=('192.0.2.1',1234)) as remote:self.assertEqual(remote.get('/health').status_code,403)
 def test_frozen_cases_expose_identity_not_outcomes(self):
  x=self.client.get('/research/cases',params={'regime':'original5-online'});self.assertEqual(x.status_code,200);self.assertTrue(x.json()['cases']);self.assertNotIn('build_result',x.text)
if __name__=='__main__':unittest.main()
