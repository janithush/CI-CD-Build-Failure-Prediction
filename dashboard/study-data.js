/* Shared schema and bounded loading for both local study views. No network retry. */
'use strict';
const StudyData=(()=>{
 const regimes=['original5-zero','later4-zero','original5-online'],models=['B0','C1','extended'];
 function finite(x,min,max){return typeof x==='number'&&Number.isFinite(x)&&x>=min&&x<=max;}
 function validate(data){
  const fail=()=>{throw Error('Research results have an invalid or incomplete schema. No results are displayed.');};
  if(!data||!Array.isArray(data.macro)||!Array.isArray(data.per_project)||data.macro.length!==9||data.per_project.length!==42)fail();
  const unique=new Set();
  for(const x of data.macro){if(!x||!regimes.includes(x.regime)||!models.includes(x.model)||!finite(x.AP,0,1)||!finite(x.Brier,0,1)||!finite(x.warning_rate,0,1)||!finite(x.false_alarms_per_100_runs,0,100))fail();const k=x.regime+'/'+x.model;if(unique.has(k))fail();unique.add(k);}
  const keys=new Set();
  for(const x of data.per_project){if(!x||!regimes.includes(x.regime)||!models.includes(x.model)||typeof x.repository!=='string'||!x.repository.includes('/')||!Number.isInteger(x.rows)||x.rows<=0||!Number.isInteger(x.failures)||x.failures<0||x.failures>x.rows||!finite(x.AP,0,1))fail();const k=x.regime+'/'+x.repository+'/'+x.model;if(keys.has(k))fail();keys.add(k);}
  for(const regime of regimes){const group=data.per_project.filter(x=>x.regime===regime),repos=new Set(group.map(x=>x.repository));if(repos.size!==(regime==='later4-zero'?4:5))fail();for(const repo of repos){const rows=group.filter(x=>x.repository===repo);if(rows.length!==3||new Set(rows.map(x=>x.rows)).size!==1||new Set(rows.map(x=>x.failures)).size!==1)fail();}}
  return data;
 }
 async function load(){if(location.protocol==='file:')throw Error('Open this dashboard through a local HTTP server, not directly as a file. See README.');const r=await fetch('research-results.json',{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Research results unavailable (HTTP '+r.status+'). Restore the frozen JSON and retry.');let x;try{x=await r.json();}catch{throw Error('Research results are not valid JSON. Restore the frozen file and retry.');}return validate(x);}
 return {validate,load};
})();
if(typeof module!=='undefined')module.exports=StudyData;
