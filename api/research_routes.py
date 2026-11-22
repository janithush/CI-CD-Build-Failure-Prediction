"""Local-only research service routes; never infer online history from incomplete data."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
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
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(status_code=422,detail='Required provider or feature metadata is invalid; no prediction made') from e

@router.get('/workflows')
def workflows(repository:str):return perform(service.workflows,repository)

@router.post('/preview')
def preview(data:Preview):return perform(service.live_cold_preview,data.repository,data.workflow_id,data.model)

@router.post('/replay')
def replay(data:Replay):return perform(service.replay_case,data.regime,data.repository,data.run_id,data.run_attempt,data.model)

@router.get('/status')
def status():
    return {'research_runtime':service.sklearn.__version__,'required_runtime':'1.7.2',
        'live_supported':'Explicit cold-onboarding prospective preview only',
        'online_live_available':False,'regimes':list(service.REGIMES),'models':list(service.MODELS),
        'notice':'Frozen replay and new prospective preview have different evidential roles.'}
