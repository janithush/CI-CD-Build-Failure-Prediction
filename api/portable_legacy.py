"""Narrow, parameter-preserving evaluator for the reviewed legacy binary RF.

No sklearn pickle is loaded during serving. This is a legacy feature contract,
not the corrected research-v2 model or evidence of prospective validity.
"""
from pathlib import Path
import hashlib,json,io
import numpy as np
import pandas as pd

EXPECTED_MANIFEST_SHA256 = '7fdd5318d9d72a31094ac1818e8aeef5d9e1bf3b6708ea92c89de23e5cce92be'

class PortableLegacy:
 def __init__(self,manifest_path):
  self.path=Path(manifest_path)
  manifest_bytes=self.path.read_bytes();self.manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest()
  if self.manifest_sha256!=EXPECTED_MANIFEST_SHA256:raise ValueError('Portable manifest is not the reviewed artifact')
  self.manifest=json.loads(manifest_bytes);m=self.manifest
  if m['format']!='legacy-rf-sigmoid-v1':raise ValueError('Unknown portable model format')
  data=self.path.with_name(m['array_file'])
  array_bytes=data.read_bytes()
  if data.parent!=self.path.parent or hashlib.sha256(array_bytes).hexdigest()!=m['array_sha256']:raise ValueError('Portable artifact integrity mismatch')
  with np.load(io.BytesIO(array_bytes),allow_pickle=False) as f:self.arrays={k:f[k].copy() for k in f.files}
  self.features=m['features'];self.numeric=m['numeric'];self.categorical=m['categorical'];a=self.arrays
  if len(a['statistics'])!=len(self.numeric) or not np.isfinite(a['statistics']).all():raise ValueError('Unsupported missing numeric training statistics')
  if len(a['scale'])!=len(self.numeric)+len(a['indicator']) or not (a['scale']>0).all():raise ValueError('Invalid scaling schema')
  if m['tree_count']!=300 or len(a['tree_offsets'])!=301:raise ValueError('Unexpected forest size')
  if m['classes']!=[0,1]:raise ValueError('Only the reviewed binary class order is supported')
  for i in range(m['tree_count']):
   lo,hi=a['tree_offsets'][i:i+2];left=a['left'][lo:hi];right=a['right'][lo:hi];feature=a['feature'][lo:hi]
   leaf=left==-1
   if not np.array_equal(leaf,right==-1):raise ValueError('Invalid leaf structure')
   if np.any(left[~leaf]<=np.flatnonzero(~leaf)) or np.any(right[~leaf]<=np.flatnonzero(~leaf)) or np.any(left[~leaf]>=hi-lo) or np.any(right[~leaf]>=hi-lo):raise ValueError('Tree is not a forward acyclic graph')
   if np.any(feature[~leaf]<0) or np.any(feature[~leaf]>=m['transformed_features']):raise ValueError('Invalid split feature')
  if not np.isfinite(a['p1']).all() or np.any((a['p1']<0)|(a['p1']>1)):raise ValueError('Invalid leaf probabilities')
 def transform(self,frame):
  missing=[x for x in self.features if x not in frame]
  if missing:raise ValueError('Legacy feature schema incomplete: '+', '.join(missing))
  a=self.arrays;numeric=frame[self.numeric].to_numpy(dtype=np.float64,na_value=np.nan);mask=np.isnan(numeric)
  if np.isinf(numeric).any():raise ValueError('Infinite model input is not supported')
  numeric=np.where(mask,a['statistics'],numeric);numeric=np.concatenate([numeric,mask[:,a['indicator']].astype(float)],axis=1)
  numeric=(numeric-a['mean'])/a['scale'];parts=[numeric]
  for i,name in enumerate(self.categorical):
   values=frame[name].to_numpy(dtype=object);values=np.array([self.manifest['category_fill'][i] if pd.isna(x) else x for x in values],dtype=object)
   # Exact category equality; unknown categories have no active one-hot column.
   parts.append(np.column_stack([values==category for category in self.manifest['categories'][i]]).astype(float))
  result=np.concatenate(parts,axis=1).astype(np.float32)
  if result.shape[1]!=self.manifest['transformed_features'] or not np.isfinite(result).all():raise ValueError('Invalid transformed feature matrix')
  return result
 def predict_proba(self,frame):
  x=self.transform(frame);a=self.arrays;total=np.zeros(len(x),dtype=np.float64);rows=np.arange(len(x))
  for i in range(self.manifest['tree_count']):
   lo,hi=a['tree_offsets'][i:i+2];node=np.zeros(len(x),dtype=np.int64)
   for _ in range(self.manifest['max_depth']+1):
    active=a['left'][lo+node]!=-1
    if not active.any():break
    r=rows[active];n=lo+node[active];go=x[r,a['feature'][n]]<=a['thresholds'][n];node[active]=np.where(go,a['left'][n],a['right'][n])
   if np.any(a['left'][lo+node]!=-1):raise ValueError('Tree traversal exceeded declared depth')
   total+=a['p1'][lo+node]
  total/=self.manifest['tree_count'];prob=1/(1+np.exp(self.manifest['sigmoid_a']*total+self.manifest['sigmoid_b']))
  return np.column_stack([1-prob,prob])
