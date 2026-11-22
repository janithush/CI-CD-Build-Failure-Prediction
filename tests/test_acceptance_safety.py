import unittest,requests,os,tempfile,ast
from unittest.mock import patch
from pathlib import Path
from fastapi.testclient import TestClient
from api.main import app
from api import research_service as service
from github_analyzer.repository_analyzer import github_headers
ROOT=Path(__file__).resolve().parents[1]
class AcceptanceSafetyTests(unittest.TestCase):
 def test_provider_denials_never_retry(self):
  for status in [401,403,404,429,500]:
   class R:status_code=status
   with patch.object(service.requests,'get',return_value=R()) as get:
    with self.assertRaises(service.ResearchUnavailable):service.PublicGitHub().get('/repos/a/b')
    self.assertEqual(get.call_count,1)
 def test_provider_timeout_fails_closed(self):
  with patch.object(service.requests,'get',side_effect=requests.Timeout):
   with self.assertRaises(service.ResearchUnavailable):service.PublicGitHub().get('/repos/a/b')
 def test_missing_private_or_stale_metadata_produces_no_score(self):
  client=TestClient(app)
  for side_effect in [[{}],[{'private':True}],[{'default_branch':'main'}, {'state':'disabled'}]]:
   with patch.object(service.PublicGitHub,'get',side_effect=side_effect):
    r=client.post('/research/preview',json={'repository':'a/b','workflow_id':1,'model':'C1'});self.assertEqual(r.status_code,422,r.text);self.assertNotIn('raw_probability',r.json())
 def test_legacy_network_errors_and_mismatch_are_visible(self):
  client=TestClient(app)
  with patch('api.main.analyze_github_repository',side_effect=requests.Timeout):self.assertEqual(client.post('/connect-github-repo',json={'repo_url':'a/b'}).status_code,503)
  from api import risk_analyzer as risk
  with patch.object(risk,'_runtime_mismatches',['controlled unsupported runtime']):self.assertEqual(client.post('/predict-connected-repo',json={'commit_id':'controlled'}).status_code,503)
 def test_legacy_headers_use_only_explicit_session_token(self):
  with patch.dict(os.environ,{'GITHUB_TOKEN':'controlled-not-real'}):self.assertNotIn('Authorization',github_headers())
  self.assertEqual(github_headers('controlled-session')['Authorization'],'Bearer controlled-session')
 def test_no_new_workflow_or_training_call(self):
  self.assertFalse(list((ROOT/'.github/workflows').glob('*.yml')))
  self.assertFalse(list((ROOT/'.github/workflows').glob('*.yaml')))
  for name in ['api/research_service.py','api/research_routes.py','api/prediction_store.py']:
   tree=ast.parse((ROOT/name).read_text())
   for n in ast.walk(tree):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute):self.assertNotIn(n.func.attr,['fit','fit_transform','partial_fit'])
 def test_repository_traversal_rejected(self):
  for repo in ['a/..','../b','a/.']:
   with self.assertRaises(service.ResearchUnavailable):service.repository_name(repo)
if __name__=='__main__':unittest.main()
