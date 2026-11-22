import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from api import research_service as service
from api.main import app

class ResearchServiceTests(unittest.TestCase):
    def test_all_nine_frozen_probability_vectors(self):
        for regime in service.REGIMES:
            d=service.frozen_frame(regime)
            expected=pd.read_csv(service.BUNDLE/'data'/(regime+'-predictions.csv.gz'))
            for model in service.MODELS:
                with self.subTest(regime=regime,model=model):
                    p,threshold,digest=service.score_frame(d,model,False)
                    if regime=='original5-online':
                        h,ht,_=service.score_frame(d,model,True)
                        p=np.where(d.history_rich,h,p)
                    self.assertLess(float(np.max(np.abs(p-expected[model]))),1e-12)
                    self.assertEqual(len(digest),64)
                    self.assertTrue(0<threshold<1)

    def test_outcome_flips_do_not_change_inference(self):
        d=service.frozen_frame('original5-zero').iloc[:3].copy()
        a=service.score_frame(d,'C1')[0]
        for name in ['build_result','conclusion','outcome_available_at']:
            if name in d:d[name]='deliberately flipped current/future outcome'
        np.testing.assert_allclose(a,service.score_frame(d,'C1')[0],atol=1e-12,rtol=0)

    def test_missing_feature_is_rejected(self):
        d=service.frozen_frame('original5-zero').iloc[:1].drop(columns=['lines_added'])
        with self.assertRaisesRegex(service.ResearchUnavailable,'Missing required'):
            service.score_frame(d,'C1')

    def test_frozen_case_endpoint_and_identity(self):
        row=service.frozen_frame('original5-online').iloc[0]
        c=TestClient(app)
        payload=dict(regime='original5-online',repository=row.repository,run_id=int(row.run_id),run_attempt=int(row.run_attempt),model='C1')
        r=c.post('/research/replay',json=payload)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['commit_id'],row.commit_id)
        self.assertEqual(r.json()['mode'],'frozen-replay')
        payload['run_id']=-1
        self.assertEqual(c.post('/research/replay',json=payload).status_code,422)

    def test_public_provider_rejects_rate_limit_without_retry(self):
        class Response: status_code=429
        with patch.object(service.requests,'get',return_value=Response()) as get:
            with self.assertRaisesRegex(service.ResearchUnavailable,'no automatic retry'):
                service.PublicGitHub().get('/repos/pallets/flask')
            self.assertEqual(get.call_count,1)

    def test_external_hosts_and_unknown_model_rejected(self):
        for value in ['https://evil.example/owner/repo','http://github.com/a/b','a/b/../../c']:
            with self.assertRaises(service.ResearchUnavailable):service.repository_name(value)
        with self.assertRaises(service.ResearchUnavailable):service.artifact('unknown')

    def test_cold_frame_excludes_history_and_is_timing_checked(self):
        # Controlled edge fixture, not provider-success evidence.
        commit={'sha':'a'*40,'commit':{'committer':{'date':'2026-01-01T00:00Z'},'message':'Test'},'parents':[{'sha':'b'*40}],
            'stats':{'additions':4,'deletions':1},'files':[{'filename':'tests/test_a.py','status':'modified'}]}
        workflow={'id':1,'name':'Tests','branch':'main'}
        d=service.cold_feature_frame('a/b',commit,workflow,'jobs: {test: {runs-on: ubuntu-latest}}','Python','2026-01-02T12:00Z')
        self.assertTrue(pd.isna(d.iloc[0].past_mean_relative_files_changed))
        self.assertNotIn('workflow_prior_failure_rate',d)
        self.assertEqual(d.iloc[0].test_files_changed,1)
        self.assertEqual(d.iloc[0].defined_jobs,1)
        self.assertEqual(d.iloc[0].declares_linux,1)
        self.assertEqual(d.iloc[0].commit_hour_utc,12)
        with self.assertRaises(service.ResearchUnavailable):
            service.cold_feature_frame('a/b',commit,workflow,None,'Python','2025-01-01T00:00Z')

if __name__=='__main__':unittest.main()
