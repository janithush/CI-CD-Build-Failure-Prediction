from pathlib import Path
import pandas as pd,json,requests,hashlib,sqlite3,time,os
from concurrent.futures import ThreadPoolExecutor
R=Path('/tmp/thesis-noncode');O=R/'responses';O.mkdir(exist_ok=True)
paths={'source':'/tmp/thesis-repair/external-results/five_features_improvement.csv','original5':'/tmp/thesis-repair/external-results/features-online.csv','later4':'/tmp/thesis-final-four/confirmation/frozen-features.csv'}
frames={k:pd.read_csv(p,dtype={'workflow_id':'string'}) for k,p in paths.items()};g=frames['later4'].groupby('repository').size();frames['later4']=frames['later4'][frames['later4'].repository.isin(g[g.ge(200)].index)]
token=os.environ.get('GITHUB_TOKEN') or os.environ['GITHUB_TOKEN']
queries=[]
for name,d in frames.items():
 for row in d[d.run_attempt.gt(1)].to_dict('records'):
  for a in range(1,int(row['run_attempt'])):queries.append(('attempt',f"https://api.github.com/repos/{row['repository']}/actions/runs/{int(row['run_id'])}/attempts/{a}"))
for row in frames['later4'].drop_duplicates(['repository','commit_id','workflow_path']).to_dict('records'):
 if isinstance(row['workflow_path'],str):queries.append(('definition',f"https://raw.githubusercontent.com/{row['repository']}/{row['commit_id']}/{row['workflow_path'].split('@')[0]}"))
queries=sorted(set(queries));start=time.monotonic()
def one(q):
 kind,url=q;p=O/(hashlib.sha256(url.encode()).hexdigest()+'.json')
 if p.exists():return
 headers={'User-Agent':'BuildRisk-Research-Collector/1.0'}
 if kind=='attempt':headers.update({'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'})
 try:
  r=requests.get(url,headers=headers,timeout=30)
  if r.status_code in [401,429] or (r.status_code==403 and r.headers.get('X-RateLimit-Remaining')=='0'):raise RuntimeError('API_STOP '+str(r.status_code))
  out={'kind':kind,'url':url,'status':r.status_code,'fetched_at':pd.Timestamp.now(tz='UTC').isoformat(),'sha256':hashlib.sha256(r.content).hexdigest(),'data':r.json() if kind=='attempt' and r.status_code==200 else r.text}
  p.write_text(json.dumps(out))
 except requests.RequestException as e:(O/(p.stem+'.error')).write_text(type(e).__name__)
for i in range(0,len(queries),4):
 if time.monotonic()-start>95:break
 with ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(one,queries[i:i+4]))
print('cached',sum((O/(hashlib.sha256(u.encode()).hexdigest()+'.json')).exists() for _,u in queries),'/',len(queries),'seconds',round(time.monotonic()-start,1),flush=True)
(R/'collection-state.json').write_text(json.dumps({'total_requested_urls':len(queries),'cached':sum((O/(hashlib.sha256(u.encode()).hexdigest()+'.json')).exists() for _,u in queries),'complete':all((O/(hashlib.sha256(u.encode()).hexdigest()+'.json')).exists() for _,u in queries)},indent=2))
