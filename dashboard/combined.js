'use strict';
(() => {
const $=id=>document.getElementById(id);
let studies=null, selectedRepository=null, generation=0, shownPrediction=null, replayCases=[];
async function request(path,body) {
 const response=await fetch(API_BASE+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(60000)});
 let data;try{data=await response.json();}catch{throw Error('API did not return readable JSON');}
 if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Request unavailable (HTTP '+response.status+')');
 return data;
}
function renderStudy(){
 const regime=$('studyRegime').value,rows=studies.macro.filter(x=>x.regime===regime);
 function cell(row,text){const c=document.createElement('td');c.textContent=text;row.append(c);}
 $('studyMacro').replaceChildren();
 for(const model of ['B0','C1','extended']){const x=rows.find(v=>v.model===model),tr=document.createElement('tr');[model,x.AP.toFixed(5),x.Brier.toFixed(5),(100*x.warning_rate).toFixed(2)+'%',x.false_alarms_per_100_runs.toFixed(2)].forEach(v=>cell(tr,v));$('studyMacro').append(tr);}
 $('studyProjects').replaceChildren();for(const x of studies.per_project.filter(v=>v.regime===regime)){const tr=document.createElement('tr');[x.repository,x.rows,x.failures,x.model,x.AP.toFixed(5)].forEach(v=>cell(tr,v));$('studyProjects').append(tr);}
 const delta=rows.find(x=>x.model==='extended').AP-rows.find(x=>x.model==='C1').AP;
 $('studyRows').textContent=regime==='later4-zero'?'1,996':'2,500';$('studyDelta').textContent=(delta>=0?'+':'')+delta.toFixed(5);
 $('studyInterval').textContent=({'original5-zero':'[-0.00845, +0.02502]','later4-zero':'[-0.02547, +0.04142]','original5-online':'[-0.06578, -0.01021]'})[regime];
 $('studyNote').textContent=regime==='original5-online'?'Frozen online released-history study, not a live history mode.':'Frozen cold-history study. No connected-repository accuracy claim.';
}
$('studyRegime').addEventListener('change',()=>{if(studies)renderStudy();});
async function loadStudy(){
 studies=null;$('studyRegime').disabled=true;$('studyRetry').disabled=true;$('studyMacro').replaceChildren();$('studyProjects').replaceChildren();
 for(const id of ['studyRows','studyDelta','studyInterval'])$(id).textContent='--';
 $('studyLoadState').textContent='Loading frozen evidence...';$('studyLoadState').setAttribute('role','status');
 try{studies=await StudyData.load();renderStudy();$('studyRegime').disabled=false;$('studyLoadState').textContent='Frozen evidence loaded. Not connected-repository performance.';}
 catch(e){$('studyLoadState').textContent=e.message;$('studyLoadState').setAttribute('role','alert');$('studyNote').textContent='Results unavailable. No fallback metrics are shown.';}
 finally{$('studyRetry').disabled=false;}
}
$('studyRetry').addEventListener('click',loadStudy);loadStudy();
function invalidate(){connectedCommitData=null;connectedPrediction=null;$('predictBtn').disabled=true;$('feedbackBtn').disabled=true;setConnectionStatus('idle','Legacy not connected');clearPredictionOutput();$('researchHistory').replaceChildren();$('exportResearchRecord').disabled=true;shownPrediction=null;$('exportResearchRecord').disabled=true;$('researchFeedback').disabled=true;generation++;selectedRepository=null;$('strictPreview').disabled=true;$('liveWorkflow').disabled=true;$('strictStatus').textContent='Repository changed. Find workflows again.';$('strictProvenance').textContent='';}
$('discoverWorkflows').addEventListener('click',async()=>{
 const epoch=++generation;selectedRepository=null;
 $('discoverWorkflows').disabled=true;$('strictPreview').disabled=true;$('liveWorkflow').disabled=true;$('strictStatus').textContent='Reading public workflow metadata...';$('strictProvenance').textContent='';
 try{
 const input=$('github_repo_url').value.trim(),data=await request('/research/workflows?repository='+encodeURIComponent(input));if(epoch!==generation)return;
 if(!data||!Array.isArray(data.workflows)||data.workflows.some(w=>!w||!/^\d+$/.test(String(w.id))||typeof w.name!=='string'||typeof w.path!=='string'))throw Error('Workflow metadata is incomplete; no preview available.');
 selectedRepository=input;$('liveWorkflow').replaceChildren();
 for(const w of data.workflows){const option=document.createElement('option');option.value=w.id;option.textContent=w.name+' ('+w.path+')';$('liveWorkflow').append(option);}
 if(!data.workflows.length)throw Error('No supported active workflows found. Nothing was triggered.');
 $('liveWorkflow').disabled=false;$('strictPreview').disabled=false;$('strictStatus').textContent='Select the workflow, then request an explicit cold-start preview.';
 }catch(e){if(epoch===generation)$('strictStatus').textContent=e.message;}finally{$('discoverWorkflows').disabled=false;}
});
$('github_repo_url').addEventListener('input',invalidate);
$('changeRepoBtn').addEventListener('click',invalidate);
$('exportResearchRecord').addEventListener('click',()=>{if(!shownPrediction)return;const url=URL.createObjectURL(new Blob([JSON.stringify(shownPrediction,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='buildrisk-'+shownPrediction.prediction_id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('liveModel').addEventListener('change',()=>{shownPrediction=null;$('exportResearchRecord').disabled=true;$('researchFeedback').disabled=true;generation++;$('strictProvenance').textContent='';$('strictStatus').textContent='Selection changed. Request a new preview.';});
$('liveWorkflow').addEventListener('change',()=>{shownPrediction=null;$('exportResearchRecord').disabled=true;$('researchFeedback').disabled=true;generation++;$('strictProvenance').textContent='';$('strictStatus').textContent='Selection changed. Request a new preview.';});
$('strictPreview').addEventListener('click',async()=>{
 if(selectedRepository!==$('github_repo_url').value.trim()){$('strictStatus').textContent='Repository changed. Find workflows again.';return;}
 const epoch=++generation;
 shownPrediction=null;$('exportResearchRecord').disabled=true;$('researchFeedback').disabled=true;$('strictProvenance').textContent='';$('strictPreview').disabled=true;$('strictStatus').textContent='Building exact-commit cold-start features and checking model...';
 try{
 const x=await request('/research/preview',{repository:selectedRepository,workflow_id:Number($('liveWorkflow').value),model:$('liveModel').value});
 if(epoch!==generation)return;
 if(!x||!Number.isFinite(x.raw_probability)||x.raw_probability<0||x.raw_probability>1||!Number.isFinite(x.threshold)||x.threshold<0||x.threshold>1||!/^([a-f0-9]{40})$/.test(x.commit_id)||!/^([a-f0-9]{64})$/.test(x.model_sha256)||!Array.isArray(x.missing_features))throw Error('Preview response has incomplete probability or provenance; no score displayed.');
 showScenario(x);
 // Keep prospective preview separate from legacy connectedPrediction and its feedback form.
 }catch(e){if(epoch!==generation)return;$('strictStatus').textContent=e.message;$('strictProvenance').textContent='No preview score was produced.';}finally{$('strictPreview').disabled=selectedRepository===null;}
});
function showScenario(x){
 if(!x||!Number.isFinite(x.raw_probability)||!Number.isFinite(x.threshold)||!Array.isArray(x.missing_features)||!/^([a-f0-9]{32})$/.test(x.prediction_id))throw Error('Saved record is missing probability or identity');
 const current=$('github_repo_url').value.trim().replace(/\/$/,'');
 if(current!==x.repository&&!current.endsWith('/'+x.repository)){$('github_repo_url').value=x.repository;selectedRepository=null;$('strictPreview').disabled=true;$('liveWorkflow').disabled=true;}
 $('exportResearchRecord').disabled=false;
 $('strictStatus').textContent=x.notice; shownPrediction=x; $('researchFeedback').disabled=!x.prediction_id; $('researchFeedbackState').textContent=x.feedback_policy||'Assessment only. No retraining.';
 $('strictProvenance').textContent='Record: '+(x.prediction_id||'unsaved')+'\nMode: '+x.mode+'\nRepository: '+x.repository+'\nRaw model probability: '+(100*x.raw_probability).toFixed(2)+'%\nModel cutoff: '+(100*x.threshold).toFixed(2)+'%\nModel: '+x.model+' / '+x.route+'\nCommit: '+x.commit_id+'\nWorkflow: '+(x.workflow_path||x.workflow_id||'not recorded')+'\nRun / attempt: '+(x.run_id||'hypothetical')+' / '+(x.run_attempt||x.attempt||'--')+'\nPrediction cutoff: '+x.cutoff+'\nContract: '+x.feature_contract+'\nArtifact: '+x.model_sha256+'\nMissing by design: '+x.missing_features.join(', ')+'\n'+(x.history_policy||'Historical replay, not a new forecast.')+'\nInput hash: '+(x.input_sha256||'not recorded');
}
$('researchFeedback').addEventListener('click',async()=>{
 if(!shownPrediction)return;const snapshot=shownPrediction;$('researchFeedback').disabled=true;
 try{const x=await request('/research/feedback',{prediction_id:snapshot.prediction_id,repository:snapshot.repository,assessment:$('researchAssessment').value});if(shownPrediction?.prediction_id===snapshot.prediction_id)$('researchFeedbackState').textContent=x.learning_status+' Record: '+x.prediction_id;}
 catch(e){$('researchFeedbackState').textContent=e.message;}
 finally{$('researchFeedback').disabled=!shownPrediction;}
});
$('researchHistoryRefresh').addEventListener('click',async()=>{
 $('researchHistory').textContent='Loading repository-scoped records...';$('researchHistoryRefresh').disabled=true;
 const repository=$('github_repo_url').value.trim();
 try{const x=await request('/research/history?repository='+encodeURIComponent(repository));if(repository!==$('github_repo_url').value.trim())return;if(!Array.isArray(x.history)||x.history.some(r=>!r||typeof r.mode!=='string'||typeof r.model!=='string'||typeof r.commit_id!=='string'||typeof r.recorded_at!=='string'||!/^([a-f0-9]{32})$/.test(r.prediction_id)))throw Error('Research history metadata is incomplete; no records displayed');$('researchHistory').replaceChildren();
 for(const record of x.history){const button=document.createElement('button');button.type='button';button.textContent=record.mode+' / '+record.model+' / '+record.commit_id.slice(0,8)+' / '+record.recorded_at;button.addEventListener('click',()=>{if(repository!==$('github_repo_url').value.trim())return;showScenario(record);$('strictLiveCard').scrollIntoView({block:'start'});});$('researchHistory').append(button);}
 if(!x.history.length)$('researchHistory').textContent='No research records for this repository.';
 }catch(e){$('researchHistory').textContent=e.message;}finally{$('researchHistoryRefresh').disabled=false;}
});
$('findReplayCases').addEventListener('click',async()=>{
 $('findReplayCases').disabled=true;$('replayPrediction').disabled=true;$('replayCase').disabled=true;const regime=$('studyRegime').value;
 try{const x=await request('/research/cases?regime='+encodeURIComponent(regime));if(regime!==$('studyRegime').value)return;if(!Array.isArray(x.cases)||!x.cases.length)throw Error('No frozen examples available');replayCases=x.cases;$('replayCase').replaceChildren();x.cases.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=c.repository+' / run '+c.run_id+' / attempt '+c.run_attempt;$('replayCase').append(o);});$('replayCase').disabled=false;$('replayPrediction').disabled=false;$('replayStatus').textContent=x.notice;}
 catch(e){$('replayStatus').textContent=e.message;}finally{$('findReplayCases').disabled=false;}
});
$('studyRegime').addEventListener('change',()=>{replayCases=[];$('replayCase').disabled=true;$('replayPrediction').disabled=true;$('replayStatus').textContent='Regime changed. Find cases again.';});
$('replayPrediction').addEventListener('click',async()=>{
 const c=replayCases[Number($('replayCase').value)];if(!c)return;$('replayPrediction').disabled=true;const epoch=++generation;
 try{const x=await request('/research/replay',{regime:$('studyRegime').value,repository:c.repository,run_id:c.run_id,run_attempt:c.run_attempt,model:$('liveModel').value});if(epoch!==generation)return;showScenario(x);$('replayStatus').textContent=x.notice;$('strictLiveCard').scrollIntoView({block:'start'});}
 catch(e){$('replayStatus').textContent=e.message;}finally{$('replayPrediction').disabled=!replayCases.length;}
});
request('/research/status').then(x=>{if(!x||typeof x.research_runtime!=='string'||typeof x.legacy_runtime_supported!=='boolean')throw Error('Runtime status unavailable');$('runtimeState').textContent='Research runtime '+x.research_runtime+'. Live preview: cold only; online history unavailable. '+(x.legacy_runtime_supported?'Legacy runtime check passed.':'Legacy inference unavailable: incompatible artifact runtime.');}).catch(e=>{$('runtimeState').textContent=e.message;});
})();
