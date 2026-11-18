from pathlib import Path
import json,numpy as np,pandas as pd
R=Path('/tmp/thesis-repair/source/research-checkpoint');d=pd.read_csv(R/'five_features_recorded.csv')
for c in ['run_started_at','outcome_available_at']:d[c]=pd.to_datetime(d[c],utc=True)
assert d.run_started_at.notna().all() and d.outcome_available_at.notna().all() and d.outcome_available_at.ge(d.run_started_at).all()
cols=['workflow_prior_runs','previous_workflow_result','workflow_prior_failure_rate','workflow_failure_rate_3','workflow_failure_rate_5','workflow_failure_rate_10','workflow_failure_rate_20','hours_since_previous_workflow_run','hours_since_previous_failure','repository_prior_runs','repository_prior_failure_rate','branch_prior_failure_rate']
out=pd.DataFrame(np.nan,index=d.index,columns=cols);affected=0
for keys,prefix in [(['repository','workflow_id'],'workflow'),(['repository'],'repository'),(['repository','branch'],'branch')]:
 for _,g in d.groupby(keys,dropna=False):
  r=g.sort_values('outcome_available_at',kind='stable');a=r.outcome_available_at.astype('int64').to_numpy();ss=r.run_started_at.astype('int64').to_numpy();y=r.build_result.to_numpy();t=g.run_started_at.astype('int64').to_numpy();k=np.searchsorted(a,t,side='left');n=k>0;j=np.maximum(0,k-1);cs=np.r_[0,np.cumsum(y)]
  rate=np.divide(cs[k],k,out=np.full(len(k),np.nan),where=n)
  if prefix=='workflow':
   out.loc[g.index,'workflow_prior_runs']=k;out.loc[g.index,'workflow_prior_failure_rate']=rate
   out.loc[g.index,'previous_workflow_result']=np.where(n,y[j],np.nan)
   out.loc[g.index,'hours_since_previous_workflow_run']=np.where(n,(t-ss[j])/3.6e12,np.nan)
   last=pd.Series(np.where(y==1,ss.astype(float),np.nan)).ffill().to_numpy();out.loc[g.index,'hours_since_previous_failure']=np.where(n,(t-last[j])/3.6e12,np.nan)
   for w in [3,5,10,20]:
    lo=np.maximum(0,k-w);out.loc[g.index,'workflow_failure_rate_'+str(w)]=np.divide(cs[k]-cs[lo],k-lo,out=np.full(len(k),np.nan),where=n)
   affected+=int((np.searchsorted(np.sort(t),t,side='left')>k).sum())
  elif prefix=='repository':out.loc[g.index,'repository_prior_runs']=k;out.loc[g.index,'repository_prior_failure_rate']=rate
  else:out.loc[g.index,'branch_prior_failure_rate']=rate
comparison={c:int((~np.isclose(out[c],d[c],equal_nan=True,atol=1e-9)).sum()) for c in cols}
report={'rows':len(d),'independent_history_field_mismatches':comparison,'rows_with_unavailable_earlier_started_workflow_outcomes':affected,'availability_proxy':'recorded updated_at, not certified exact completion','missing_or_before_start_availability':0}
Path('/tmp/thesis-repair/independent-history-audit.json').write_text(json.dumps(report,indent=2));out.to_csv('/tmp/thesis-repair/rebuilt-history.csv',index=False);print(json.dumps(report,indent=2));assert not any(comparison.values()),comparison
