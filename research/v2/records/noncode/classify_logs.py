from pathlib import Path
import json,re,sqlite3,zipfile,hashlib,collections,pandas as pd,tarfile
R=Path('/tmp/thesis-noncode');L=R/'raw-logs';x=json.load(open('/tmp/gate-download-map.json'))
for v in x.values():
 if v['metadata']['name']=='exact-checkpoint-20261117-160950.tar.gz':
  with tarfile.open(v['download']['file_path']) as t:
   for m in t.getmembers():
    if '/logs/' in m.name and m.name.endswith('.zip'):(L/Path(m.name).name).write_bytes(t.extractfile(m).read())
c=sqlite3.connect(R/'latest-evidence.sqlite3');jobs=collections.defaultdict(dict)
for u,b in c.execute("select url,body from responses where url like '%/jobs?%'"):
 repo=u.split('/repos/')[1].split('/actions/')[0]
 for j in json.loads(b).get('jobs',[]):jobs[(repo,int(j['run_id']),int(j.get('run_attempt',1)))][j['id']]=j
rules={'network_resolution':r'could not resolve|temporary failure in name resolution|name or service not known|network is unreachable|connection (?:reset|refused|aborted)|connecttimeout|connectionerror|readtimeout|remote(disconnected|error)|sslerror|httperror|HTTP (?:Error )?(?:429|500|502|503|504)|TLS handshake|\bECONNRESET\b|\bENOTFOUND\b', 'timeout':r'\bGateway Timeout\b|\b(?:operation|connection|request|read|build|test|process) timed out\b|\bTimeout(?:Error|Expired):|\bexceeded (?:the )?(?:time limit|time budget)\b|\boperation was canceled\b', 'dependency_environment':r'no matching distribution found|could not find a version that satisfies|resolutionimpossible|modulenotfounderror|importerror|no space left on device|disk quota exceeded|cannot allocate memory|out of memory|killed process', 'compile_build':r'fatal error:|error:.*(?:undeclared|undefined reference|cannot convert|no member named)|compilation terminated|compileerror|error C[0-9]{4}|ninja: build stopped|ld:.*(?:error|undefined)', 'assertion':r'assertionerror|^\s*FAILED .* - assert\b|^\s*E\s+assert\b', 'test_failure_summary':r'\b[1-9][0-9]* failed\b|FAILED \((?:[^\n]*failures=[1-9])|^\s*FAIL: '}
compiled={k:re.compile(v,re.I) for k,v in rules.items()};ansi=re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]');timestamp=re.compile(r'^\ufeff?(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.\d+)?Z\s?(.*)$')
m=pd.read_csv('/tmp/thesis-repair/external-results/frozen-log-membership.csv');outputs=[];pointers=[]
for row in m.to_dict('records'):
 key=(row['repository'],int(row['run_id']),int(row['run_attempt']));p=L/(str(row['archive_path']).split('/')[-1]);out={k:row[k] for k in ['repository','run_id','run_attempt','conclusion','label','log_status']};out.update({k:False for k in rules});out['scope_category']='success' if row['conclusion']=='success' else 'unknown';out['parse_status']='missing';out['failed_steps_with_matched_logs']=0;out['failed_steps_total']=0
 if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['archive_sha256']:
  with zipfile.ZipFile(p) as z:
   infos=[i for i in z.infolist() if '/' not in i.filename and i.filename.endswith('.txt')];total=sum(i.file_size for i in infos)
   if total>100*1024*1024:out['parse_status']='oversized_bound'
   else:
    texts=collections.defaultdict(list)
    for info in infos:
     text=z.read(info).decode('utf-8-sig',errors='replace');match=re.search(r'Complete job name: ([^\r\n]+)',text)
     if match:texts[match.group(1)].append((info.filename,text))
    out['parse_status']='parsed'
    for j in jobs[key].values():
     if j.get('conclusion')!='failure':continue
     for step in j.get('steps',[]):
      if step.get('conclusion')!='failure':continue
      out['failed_steps_total']+=1;lo=step.get('started_at');hi=step.get('completed_at');choices=texts.get(j['name'],[])
      if not lo or not hi or len(choices)!=1:continue
      out['failed_steps_with_matched_logs']+=1;entry,text=choices[0]
      for num,line in enumerate(text.splitlines(),1):
       a=timestamp.match(line)
       if not a or not (lo[:19]<=a[1]<=hi[:19]):continue
       clean=ansi.sub('',a[2])
       for category,rx in compiled.items():
        if rx.search(clean) and not (category=='timeout' and re.search(r'spell|docs',step['name'],re.I)):out[category]=True;pointers.append({'repository':key[0],'run_id':key[1],'run_attempt':key[2],'job_id':j['id'],'step_number':step['number'],'step_name':step['name'],'entry':entry,'line':num,'category':category,'text':clean[:1000],'interval_caveat':'inclusive API seconds, not exact subsecond boundaries'})
    if row['conclusion']=='failure':
     code=out['assertion'] or out['test_failure_summary'] or out['compile_build'];env=out['network_resolution'] or out['timeout'] or out['dependency_environment'];out['scope_category']='mixed_observed_signatures' if code and env else 'test_or_compile_supported' if code else 'environment_like_supported' if env else 'unknown'
 else:
  if p.is_file():out['parse_status']='hash_mismatch'
 outputs.append(out)
o=pd.DataFrame(outputs);o.to_csv(R/'log-classification.csv',index=False);pd.DataFrame(pointers).to_csv(R/'log-evidence-pointers.csv',index=False);print(o.groupby(['conclusion','parse_status','scope_category']).size().to_string());print('pointers',len(pointers));print('failure steps coverage',o.failed_steps_with_matched_logs.sum(),'/',o.failed_steps_total.sum());print(o[o.conclusion.eq('failure')].groupby('repository')[list(rules)].sum().to_string())
