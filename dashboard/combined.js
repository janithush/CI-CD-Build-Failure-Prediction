'use strict';
(() => {
const $=id=>document.getElementById(id);
let studies=null, selectedRepository=null;
async function request(path,body) {
 const response=await fetch(API_BASE+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(60000)});
 let data;try{data=await response.json();}catch{throw Error('API did not return readable JSON');}
 if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Request unavailable');
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
$('studyRegime').addEventListener('change',renderStudy);
fetch('research-results.json').then(r=>{if(!r.ok)throw Error('Research results unavailable');return r.json();}).then(x=>{studies=x;renderStudy();}).catch(e=>{$('studyNote').textContent=e.message;});
$('discoverWorkflows').addEventListener('click',async()=>{
 $('discoverWorkflows').disabled=true;$('strictPreview').disabled=true;$('liveWorkflow').disabled=true;$('strictStatus').textContent='Reading public workflow metadata...';$('strictProvenance').textContent='';
 try{
 const input=$('github_repo_url').value.trim(),data=await request('/research/workflows?repository='+encodeURIComponent(input));selectedRepository=input;$('liveWorkflow').replaceChildren();
 for(const w of data.workflows){const option=document.createElement('option');option.value=w.id;option.textContent=w.name+' ('+w.path+')';$('liveWorkflow').append(option);}
 if(!data.workflows.length)throw Error('No supported active workflows found. Nothing was triggered.');
 $('liveWorkflow').disabled=false;$('strictPreview').disabled=false;$('strictStatus').textContent='Select the workflow, then request an explicit cold-start preview.';
 }catch(e){$('strictStatus').textContent=e.message;}finally{$('discoverWorkflows').disabled=false;}
});
$('github_repo_url').addEventListener('input',()=>{selectedRepository=null;$('strictPreview').disabled=true;$('liveWorkflow').disabled=true;$('strictStatus').textContent='Repository changed. Find workflows again.';});
$('strictPreview').addEventListener('click',async()=>{
 if(selectedRepository!==$('github_repo_url').value.trim()){$('strictStatus').textContent='Repository changed. Find workflows again.';return;}
 $('strictPreview').disabled=true;$('strictStatus').textContent='Building exact-commit cold-start features and checking model...';
 try{
 const x=await request('/research/preview',{repository:selectedRepository,workflow_id:Number($('liveWorkflow').value),model:$('liveModel').value});
 $('strictStatus').textContent=x.notice;
 $('strictProvenance').textContent='Raw model probability: '+(100*x.raw_probability).toFixed(2)+'%\nModel cutoff: '+(100*x.threshold).toFixed(2)+'%\nModel: '+x.model+' / '+x.route+'\nCommit: '+x.commit_id+'\nWorkflow: '+x.workflow_path+'\nScenario cutoff: '+x.cutoff+'\nContract: '+x.feature_contract+'\nArtifact: '+x.model_sha256+'\nMissing by design: '+x.missing_features.join(', ')+'\n'+x.history_policy;
 // Keep prospective preview separate from legacy connectedPrediction and its feedback form.
 }catch(e){$('strictStatus').textContent=e.message;$('strictProvenance').textContent='No preview score was produced.';}finally{$('strictPreview').disabled=selectedRepository===null;}
});
request('/research/status').then(x=>{$('runtimeState').textContent='Research runtime '+x.research_runtime+'. Live preview: cold only; online history unavailable. '+(x.legacy_runtime_supported?'Legacy runtime check passed.':'Legacy inference unavailable: incompatible artifact runtime.');}).catch(e=>{$('runtimeState').textContent=e.message;});
})();
