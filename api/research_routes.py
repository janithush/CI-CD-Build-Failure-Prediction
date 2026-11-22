"""Local-only research service routes; never infer online history from incomplete data."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
import sqlite3
from api import prediction_store as store
from api import research_service as service

router=APIRouter(prefix='/research',tags=['Research models'])
class Preview(BaseModel):
    repository:str
    workflow_id:int=Field(gt=0)
    model:str='C1'
class Replay(BaseModel):
    regime:str
    repository:str
    run_id:int
    run_attempt:int=Field(ge=1)
    model:str='C1'

def perform(function,*args):
    try:return function(*args)
    except service.ResearchUnavailable as e:raise HTTPException(status_code=422,detail=str(e))
    except sqlite3.Error as e:raise HTTPException(status_code=503,detail='Local record store unavailable; no stored prediction confirmed') from e
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(status_code=422,detail='Required provider or feature metadata is invalid; no prediction made') from e

@router.get('/workflows')
def workflows(repository:str):return perform(service.workflows,repository)

@router.post('/preview')
def preview(data:Preview):return perform(lambda:store.save(service.live_cold_preview(data.repository,data.workflow_id,data.model)))

@router.post('/replay')
def replay(data:Replay):return perform(lambda:store.save(service.replay_case(data.regime,data.repository,data.run_id,data.run_attempt,data.model)))

@router.get('/status')
def status():
    from api.risk_analyzer import _runtime_mismatches
    return {'legacy_runtime_supported':not bool(_runtime_mismatches), 'legacy_runtime_mismatches':_runtime_mismatches, 'research_runtime':service.sklearn.__version__,'required_runtime':'1.7.2',
        'live_supported':'Explicit cold-onboarding prospective preview only',
        'online_live_available':False,'regimes':list(service.REGIMES),'models':list(service.MODELS),
        'notice':'Frozen replay and new prospective preview have different evidential roles.'}

class Feedback(BaseModel):
    model_config=ConfigDict(extra='forbid')
    prediction_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    repository:str
    assessment:Literal['helpful','unclear','not-helpful']

@router.get('/history')
def history(repository:str):
    repository=perform(service.repository_name,repository)
    return {'history':perform(store.history,repository),'scope':'Single-user local records for the exact repository only; not a scientific evaluation.'}

@router.get('/predictions/{prediction_id}')
def prediction(prediction_id:str,repository:str):
    repository=perform(service.repository_name,repository)
    try:return store.get(prediction_id,repository)
    except KeyError as e:raise HTTPException(status_code=404,detail='Prediction not found for this repository') from e

@router.post('/feedback')
def feedback(data:Feedback):
    repository=perform(service.repository_name,data.repository)
    try:return store.feedback(data.prediction_id,repository,data.assessment)
    except KeyError as e:raise HTTPException(status_code=404,detail='Prediction not found for this repository') from e

@router.get('/cases')
def cases(regime:str):
    frame=perform(service.frozen_frame,regime)
    # Small, deterministic example list. Outcomes are not returned as inference inputs.
    rows=frame.groupby('repository',sort=True).head(3)
    return {'regime':regime,'cases':[{'repository':r.repository,'run_id':int(r.run_id),'run_attempt':int(r.run_attempt),'commit_id':r.commit_id} for _,r in rows.iterrows()], 'notice':'Historical cases with known outcomes, not new forecasts.'}
