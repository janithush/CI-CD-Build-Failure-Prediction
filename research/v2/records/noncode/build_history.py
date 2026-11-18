from pathlib import Path
import pandas as pd,numpy as np,json,heapq
R=Path('/tmp/thesis-noncode');K=['repository','run_id','run_attempt'];contract=json.load(open(R/'feature-contract.json'));HIST=contract['history']
pairs=pd.read_csv(R/'rerun-pairs.csv',dtype={'workflow_id':'string'});pairs['available_at']=pd.to_datetime(pairs.available_at,utc=True)
# For history only, release a single pair per run: first observed binary pair, not all pair combinations.
valid=pairs[pairs.same_recorded_head_and_workflow & pairs.available_at.notna() & pairs.earlier_conclusion.isin(['success','failure']) & pairs.later_conclusion.isin(['success','failure'])].sort_values('available_at').drop_duplicates(['repository','run_id'])
def history(d,name,pairdata=valid):
 d=d.copy().reset_index(drop=True);times=pd.to_datetime(d.run_started_at,utc=True);available=pd.to_datetime(d.outcome_available_at,utc=True,errors='coerce');allowed=available.notna()&available.ge(times)
 if name=='original5-online':allowed &= d.complete_jobs.eq(1)
 events=[]
 for i in d.index[allowed]:events.append((available.iloc[i].value,0,i))
 repos=set(d.repository)
 for i,r in pairdata[pairdata.repository.isin(repos)].iterrows():events.append((r.available_at.value,1,int(i)))
 events.sort();cursor=0;state={};heads={};pstate={};result=np.full((len(d),len(HIST)),np.nan)
 for i in sorted(d.index,key=lambda k:(times.iloc[k].value,k)):
  now=times.iloc[i].value
  while cursor<len(events) and events[cursor][0]<now:
   _,kind,k=events[cursor];cursor+=1
   if kind==0:
    r=d.iloc[k];wf=(r.repository,str(r.workflow_id));head=(*wf,r.commit_id);fail=int(r.build_result);state[wf]=state.get(wf,0)+1 if fail else 0;cnt,nfail=heads.get(head,(0,0));heads[head]=(cnt+1,nfail+fail)
   else:
    r=pairdata.loc[k];wf=(r.repository,str(r.workflow_id));n,discord=pstate.get(wf,(0,0));pstate[wf]=(n+1,discord+int(r.discordant))
  r=d.iloc[i];wf=(r.repository,str(r.workflow_id));cnt,nfail=heads.get((*wf,r.commit_id),(0,0));n,disc=pstate.get(wf,(0,0));result[i]=[state.get(wf,0),cnt,nfail/cnt if cnt else np.nan,disc,n,disc/n if n else np.nan]
 for k,c in enumerate(HIST):d[c]=result[:,k]
 return d
checks=[]
for name in ['source','original5-online']:
 d=pd.read_csv(R/(name+'-static.csv'),dtype={'workflow_id':'string'});out=history(d,name);out.to_csv(R/(name+'-history.csv'),index=False);times=pd.to_datetime(d.run_started_at,utc=True)
 cut=times.sort_values().iloc[len(d)//2];mask=times.le(cut);prefix=d[mask].reset_index(drop=True);a=history(prefix,name);pd.testing.assert_frame_equal(out.loc[mask,HIST].reset_index(drop=True),a[HIST]);checks.append(name+': chronological prefix invariant')
 flipped=d.copy();flipped.loc[times.ge(cut),'build_result']=1-flipped.loc[times.ge(cut),'build_result'];b=history(flipped,name);pd.testing.assert_frame_equal(out.loc[mask,HIST].reset_index(drop=True),b.loc[mask,HIST].reset_index(drop=True));checks.append(name+': current/future outcome flips invariant')
 # Removing pair records not released before cutoff must not change earlier features.
 a=history(d,name,valid[valid.available_at.lt(cut)]);pd.testing.assert_frame_equal(out.loc[times.le(cut),HIST],a.loc[times.le(cut),HIST]);checks.append(name+': future pair removal invariant')
print('PASSED',checks);(R/'HISTORY_CHECKS.json').write_text(json.dumps({'checks':checks,'rule':'release strictly before prediction start; complete terminal-job condition on original external online outcomes; source updated_at proxy remains'},indent=2))
