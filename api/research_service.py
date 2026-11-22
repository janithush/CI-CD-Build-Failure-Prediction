"""Strict frozen-model serving and explicit cold-onboarding live previews.

Derived feature definitions retain upstream/research rights; no blanket MIT grant.
No fitting, outcome collection, workflow triggering or client-uploaded models.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from functools import lru_cache
import hashlib, importlib.util, json, math, re, os
import joblib
import numpy as np
import pandas as pd
import requests
import sklearn
import yaml

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'research/v2'
MODELS = ('B0', 'C1', 'extended')
REGIMES = ('original5-zero', 'later4-zero', 'original5-online')
class ResearchUnavailable(ValueError):
    pass

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

FILES = module('research_files', BUNDLE / 'records/repair/build_research_features.py')
CONTEXT = module('research_context', BUNDLE / 'src/improvement_features.py')

def clean(value):
    if isinstance(value, dict): return {str(k): clean(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [clean(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.bool_,)): return bool(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, pd.Timestamp): return value.isoformat()
    return value

@lru_cache(maxsize=6)
def artifact(name, history=False):
    if name not in MODELS: raise ResearchUnavailable('Unknown model')
    if sklearn.__version__ != '1.7.2':
        raise ResearchUnavailable('Research models require the recorded scikit-learn 1.7.2 runtime')
    p = BUNDLE / 'models' / (name + ('-history' if history else '-no-history') + '.joblib')
    expected = json.loads((ROOT/'tests/fixtures/combined/frozen-research-hashes.json').read_text())[str(p.relative_to(ROOT))]
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if digest != expected: raise ResearchUnavailable('Research artifact hash does not match the reviewed frozen artifact')
    a = joblib.load(p)
    return a, digest

def score_frame(frame, name, history=False):
    a, digest = artifact(name, history)
    missing = [x for x in a['features'] if x not in frame]
    if missing: raise ResearchUnavailable('Missing required feature columns: '+', '.join(missing))
    probability = a['model'].predict_proba(frame[a['features']])[:,1]
    return probability, float(a['source_threshold']), digest

def frozen_frame(regime):
    if regime not in REGIMES: raise ResearchUnavailable('Unknown research regime')
    features = 'original5-online-history' if regime == 'original5-online' else regime+'-static'
    return pd.read_csv(BUNDLE/'data'/(features+'.csv.gz'), dtype={'workflow_id':'string'})

def replay_case(regime, repository, run_id, run_attempt, name):
    d = frozen_frame(regime)
    d = d[d.repository.eq(repository)&d.run_id.eq(run_id)&d.run_attempt.eq(run_attempt)]
    if len(d)!=1: raise ResearchUnavailable('Research case not found or not unique')
    row=d.iloc[0];rich=regime=='original5-online' and bool(row.history_rich)
    p, threshold, digest=score_frame(d,name,rich)
    # Match original routing: history/no-history branches have their own thresholds.
    return clean({'mode':'frozen-replay','raw_probability':float(p[0]),'threshold':threshold,
        'model':name,'model_sha256':digest,'route':'history' if rich else 'no-history',
        'repository':repository,'commit_id':row.commit_id,'run_id':run_id,'run_attempt':run_attempt,
        'cutoff':str(row.run_started_at),'regime':regime,'feature_contract':'research-v2-frozen-v1',
        'missing_features':[x for x in artifact(name,rich)[0]['features'] if pd.isna(row[x])],
        'notice':'Historical replay, not a forecast for a new build.'})

class PublicGitHub:
    """Bounded public-metadata reader. Optional explicit read token stays server-side."""
    def __init__(self): self.sources=[]
    def get(self, path, params=None):
        url='https://api.github.com'+path
        try:
            headers={'Accept':'application/vnd.github+json','User-Agent':'BuildRisk-local-preview'}
            token=os.environ.get('BUILDRISK_PUBLIC_READ_TOKEN','').strip()
            if token:headers['Authorization']='Bearer '+token
            r=requests.get(url,params=params,headers=headers,timeout=20)
        except requests.RequestException as e:
            raise ResearchUnavailable('GitHub network request failed; retry later') from e
        if r.status_code != 200:
            if r.status_code in (403,429):raise ResearchUnavailable('GitHub access/rate limit; preview unavailable, no automatic retry')
            raise ResearchUnavailable('GitHub returned HTTP '+str(r.status_code)+'; preview unavailable')
        self.sources.append(r.url)
        return r.json()

def repository_name(value):
    match=re.fullmatch(r'(?:https://github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?',value.strip())
    if not match:raise ResearchUnavailable('Use a public owner/repository name or an https://github.com/owner/repository URL')
    return match.group(1)

def workflows(value):
    repo=repository_name(value);provider=PublicGitHub()
    info=provider.get('/repos/'+repo)
    if info.get('private'):raise ResearchUnavailable('This preview supports public repositories only')
    data=provider.get('/repos/'+repo+'/actions/workflows',{'per_page':100})
    items=[{'id':str(x['id']),'name':x['name'],'path':x['path']} for x in data.get('workflows',[]) if x.get('state')=='active' and x.get('path','').startswith('.github/workflows/')]
    return {'repository':repo,'workflows':items,'sources':provider.sources,'notice':'Only the first 100 declared workflows are inspected; selecting one does not trigger it.'}

STATIC = ['run_hour_sin', 'run_hour_cos', 'run_week_sin', 'run_week_cos', 'attempt_index', 'yaml_missing', 'defined_jobs', 'matrix_axis_count', 'matrix_axis_product_sum', 'matrix_include_entries', 'matrix_exclude_entries', 'reusable_jobs', 'dynamic_definition', 'declares_linux', 'declares_windows', 'declares_macos', 'declares_self_hosted']

def static(content):
 out={c:np.nan for c in STATIC[5:]};out['yaml_missing']=1
 if content is None:return out
 try:d=yaml.safe_load(content)
 except yaml.YAMLError:return out
 if not isinstance(d,dict) or not isinstance(d.get('jobs'),dict):return out
 jobs=d['jobs'];out.update({c:0. for c in STATIC[5:]});out['defined_jobs']=len(jobs)
 for j in jobs.values():
  if not isinstance(j,dict):continue
  if 'uses' in j:out['reusable_jobs']+=1
  matrix=(j.get('strategy') or {}).get('matrix',{}) if isinstance(j.get('strategy',{}),dict) else {}
  if not isinstance(matrix,dict):out['dynamic_definition']=1;matrix={}
  axes=[v for k,v in matrix.items() if k not in ['include','exclude']];out['matrix_axis_count']+=len(axes)
  if axes:
   if all(isinstance(v,list) and all('${{' not in str(z) for z in v) for v in axes):out['matrix_axis_product_sum']+=math.prod(len(v) for v in axes)
   else:out['dynamic_definition']=1;out['matrix_axis_product_sum']=np.nan
  for label in ['include','exclude']:
   v=matrix.get(label,[])
   if isinstance(v,list):out['matrix_'+label+'_entries']+=len(v)
   else:out['dynamic_definition']=1
  text=json.dumps({'runs-on':j.get('runs-on'),'matrix':matrix}).lower()
  if '${{' in text:out['dynamic_definition']=1
  for key,rx in [('linux','ubuntu|linux'),('windows','windows'),('macos','macos'),('self_hosted','self-hosted')]:out['declares_'+key]=max(out['declares_'+key],int(bool(re.search(rx,text))))
 return out

def cold_feature_frame(repo, commit, workflow, content, language, cutoff):
    """Same first-boundary cold static definitions, deliberately zero target history."""
    when=pd.Timestamp(cutoff)
    if when.tzinfo is None:raise ResearchUnavailable('Prediction cutoff must include a timezone')
    when=when.tz_convert('UTC')
    committed=pd.Timestamp(commit['commit']['committer']['date'])
    if committed>when:raise ResearchUnavailable('Commit timestamp is after prediction cutoff')
    files=commit.get('files',[])
    if not files:raise ResearchUnavailable('Complete commit file metadata is required')
    records=[{'repository':repo,'commit_id':commit['sha'],'filename':x['filename'],
              'extension':(Path(x['filename']).name.lower() if Path(x['filename']).name.startswith('.') and Path(x['filename']).name.count('.')==1 else Path(x['filename']).suffix.lower()),'change_status':x['status']} for x in files]
    row=FILES.aggregate_files(pd.DataFrame(records)).iloc[0].to_dict()
    row.update({'files_changed':len(files),'lines_added':int(commit['stats']['additions']),
        'lines_deleted':int(commit['stats']['deletions']),'message_length':len(commit['commit']['message']),
        'is_merge':int(len(commit.get('parents',[]))>1),'parent_count':len(commit.get('parents',[])),
        'commit_hour_utc':when.hour,'commit_day_of_week':when.dayofweek,'is_weekend':int(when.dayofweek>=5),
        'run_started_at':when,'repository':repo,'workflow_id':str(workflow['id']),
        'workflow_name':workflow['name'],'event':'push','branch':workflow['branch'],
        'primary_language':language or 'unknown','attempt_index':1})
    row['churn_per_file']=(row['lines_added']+row['lines_deleted'])/max(1,row['files_changed'])
    hour=when.hour+when.minute/60;week=when.dayofweek+hour/24
    row.update({'run_hour_sin':np.sin(2*np.pi*hour/24),'run_hour_cos':np.cos(2*np.pi*hour/24),
        'run_week_sin':np.sin(2*np.pi*week/7),'run_week_cos':np.cos(2*np.pi*week/7)})
    row.update(static(content))
    return CONTEXT.add_change_context(pd.DataFrame([row]))

def live_cold_preview(value, workflow_id, model='C1'):
    repo=repository_name(value);g=PublicGitHub();info=g.get('/repos/'+repo)
    if info.get('private'):raise ResearchUnavailable('This preview supports public repositories only')
    branch=info['default_branch']
    selected=g.get('/repos/'+repo+'/actions/workflows/'+str(int(workflow_id)))
    if selected.get('state')!='active' or not selected.get('path','').startswith('.github/workflows/'):
        raise ResearchUnavailable('Select an active repository workflow')
    commit=g.get('/repos/'+repo+'/commits/'+requests.utils.quote(branch,safe=''),{'per_page':100})
    sha=commit['sha'];files=commit.get('files',[])
    for page in (2,3):
        if len(files)<100*(page-1):break
        part=g.get('/repos/'+repo+'/commits/'+sha,{'per_page':100,'page':page}).get('files',[]);files.extend(part)
        if len(part)<100:break
    if len(files)>=300:raise ResearchUnavailable('Commit may be truncated at the 300-file preview limit; no prediction made')
    commit['files']=files
    content_response=g.get('/repos/'+repo+'/contents/'+selected['path'],{'ref':sha})
    if content_response.get('encoding')!='base64':raise ResearchUnavailable('Workflow definition could not be read at exact commit')
    import base64
    content=base64.b64decode(content_response['content']).decode('utf-8')
    if len(content)>200000:raise ResearchUnavailable('Workflow definition exceeds safe preview size limit')
    cutoff=datetime.now(timezone.utc).isoformat();selected['branch']=branch
    frame=cold_feature_frame(repo,commit,selected,content,info.get('language'),cutoff)
    p,threshold,digest=score_frame(frame,model,False)
    return clean({'mode':'prospective-cold-preview','model':model,'raw_probability':float(p[0]),
        'threshold':threshold,'model_sha256':digest,'route':'no-history','repository':repo,
        'commit_id':sha,'workflow_id':str(selected['id']),'workflow_path':selected['path'],
        'cutoff':cutoff,'attempt':1,'event_scenario':'push-at-preview-time',
        'feature_contract':'cold-boundary-static-v1','missing_features':[x for x in artifact(model,False)[0]['features'] if pd.isna(frame.iloc[0][x])],
        'history_policy':'All target outcomes withheld; prior change context starts empty at this explicit cold boundary.',
        'notice':'Scenario preview for a first push attempt at the displayed time, not a prediction for an already observed run. No workflow is triggered. Not validated live accuracy. Online-history live mode remains unavailable.',
        'sources':g.sources})
