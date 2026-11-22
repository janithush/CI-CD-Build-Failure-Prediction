'use strict';
(() => {
const $=id=>document.getElementById(id);
let studies=null, selectedRepository=null, generation=0;
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
function invalidate(){generation++;selectedRepository=null;$('strictPreview').disabled=true;$('liveWorkflow').disabled=true;$('strictStatus').textContent='Repository changed. Find workflows again.';$('strictProvenance').textContent='';}
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
$('liveModel').addEventListener('change',()=>{generation++;$('strictProvenance').textContent='';$('strictStatus').textContent='Selection changed. Request a new preview.';});
$('liveWorkflow').addEventListener('change',()=>{generation++;$('strictProvenance').textContent='';$('strictStatus').textContent='Selection changed. Request a new preview.';});
$('strictPreview').addEventListener('click',async()=>{
 if(selectedRepository!==$('github_repo_url').value.trim()){$('strictStatus').textContent='Repository changed. Find workflows again.';return;}
 const epoch=++generation;
 $('strictProvenance').textContent='';$('strictPreview').disabled=true;$('strictStatus').textContent='Building exact-commit cold-start features and checking model...';
 try{
 const x=await request('/research/preview',{repository:selectedRepository,workflow_id:Number($('liveWorkflow').value),model:$('liveModel').value});
 if(epoch!==generation)return;
 if(!x||!Number.isFinite(x.raw_probability)||x.raw_probability<0||x.raw_probability>1||!Number.isFinite(x.threshold)||x.threshold<0||x.threshold>1||!/^([a-f0-9]{40})$/.test(x.commit_id)||!/^([a-f0-9]{64})$/.test(x.model_sha256)||!Array.isArray(x.missing_features))throw Error('Preview response has incomplete probability or provenance; no score displayed.');
 $('strictStatus').textContent=x.notice;
 $('strictProvenance').textContent='Raw model probability: '+(100*x.raw_probability).toFixed(2)+'%\nModel cutoff: '+(100*x.threshold).toFixed(2)+'%\nModel: '+x.model+' / '+x.route+'\nCommit: '+x.commit_id+'\nWorkflow: '+x.workflow_path+'\nScenario cutoff: '+x.cutoff+'\nContract: '+x.feature_contract+'\nArtifact: '+x.model_sha256+'\nMissing by design: '+x.missing_features.join(', ')+'\n'+x.history_policy;
 // Keep prospective preview separate from legacy connectedPrediction and its feedback form.
 }catch(e){if(epoch!==generation)return;$('strictStatus').textContent=e.message;$('strictProvenance').textContent='No preview score was produced.';}finally{$('strictPreview').disabled=selectedRepository===null;}
});
request('/research/status').then(x=>{if(!x||typeof x.research_runtime!=='string'||typeof x.legacy_runtime_supported!=='boolean')throw Error('Runtime status unavailable');$('runtimeState').textContent='Research runtime '+x.research_runtime+'. Live preview: cold only; online history unavailable. '+(x.legacy_runtime_supported?'Legacy runtime check passed.':'Legacy inference unavailable: incompatible artifact runtime.');}).catch(e=>{$('runtimeState').textContent=e.message;});
})();
