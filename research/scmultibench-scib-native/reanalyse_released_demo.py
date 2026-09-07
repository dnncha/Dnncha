"""Reanalyse scMultiBench's released embedding demo for ASW/iASW defects.

Downloads only immutable, hash-verified released inputs. The numerical metric
body uses sklearn silhouette_samples; scib v1.1.5's source-verified silhouette
is exactly mean(silhouette_samples), scaled from [-1,1] to [0,1]. The native
synthetic companion test verifies the scib functions themselves.
"""
from __future__ import annotations
import hashlib, importlib.metadata, json, platform
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import h5py
import numpy as np
import pandas as pd
from sklearn import set_config
from sklearn.metrics import silhouette_samples

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'released-demo-results'; INPUT=OUT/'inputs'
COMMIT='0c68f87d554a52e363dbfda2a9d1fa9538eeae9f'
FILES={
 'data/dr&bc/embedding/cty1.csv':'bc04ec13316d61b673827fe6cc028787284bd341',
 'data/dr&bc/embedding/cty2.csv':'a156ed8c1165b6abe57985487f2d3d70bb389b56',
 'data/dr&bc/embedding/cty3.csv':'1b69f1c6c1be922dde3c41fa13641657c4f8175a',
 'data/dr&bc/embedding/embedding.h5':'203bbdbacaa345fb898ce26fa7b53322c12fe471',
 'data/clustering/embedding/sinfonia_clustering.h5':'445b9c4d41e24a46344b37611e79a52a29911d84',
}

def git_blob(raw): return hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
def fetch():
    INPUT.mkdir(parents=True,exist_ok=True); records={}
    for path,expected in FILES.items():
        name=Path(path).name; local=INPUT/name
        url='https://raw.githubusercontent.com/PYangLab/scMultiBench/'+COMMIT+'/'+quote(path,safe='/')
        if local.exists(): raw=local.read_bytes()
        else:
            with urlopen(Request(url,headers={'User-Agent':'CheerfulDuck-scientific-code-audit'}),timeout=60) as r: raw=r.read(5_000_001)
        if len(raw)>5_000_000: raise ValueError('Unexpected size '+path)
        actual=git_blob(raw)
        if actual!=expected: raise ValueError(f'Git blob mismatch {path}: {actual} != {expected}')
        local.write_bytes(raw); records[path]={'local':str(local.relative_to(ROOT)),'url':url,'bytes':len(raw),'git_blob_sha1':actual,'sha256':hashlib.sha256(raw).hexdigest()}
    return records

def read_labels(paths):
    parts=[]; names=[]
    for p in paths:
        frame=pd.read_csv(p,header=None,index_col=False)
        s=frame.iloc[1:frame.shape[0],1].reset_index(drop=True)
        parts.append(s); names.extend(s.astype(str).tolist())
    all_labels=pd.concat(parts,ignore_index=True)
    cat=pd.Categorical(all_labels)
    return np.asarray(cat.codes,dtype='int32'),np.asarray(names,dtype=object),list(cat.categories)

def read_batches(paths):
    out=[]
    for i,p in enumerate(paths):
        frame=pd.read_csv(p,header=None,index_col=False)
        s=frame.iloc[1:frame.shape[0],1]
        out.append(np.ones(len(s))+i)
    return np.concatenate(out)

def read_embedding(path):
    with h5py.File(path,'r') as f: x=np.asarray(np.array(f['data']))
    if x.shape[0]<x.shape[1]: x=x.T
    return x

def read_cluster(path):
    with h5py.File(path,'r') as f: x=np.array(f['/obs/cluster_leiden'])
    return np.array([v.decode('utf-8') if isinstance(v,(bytes,np.bytes_)) else str(v) for v in x.flatten()])

def selected_labels(labels,batches,threshold):
    df=pd.DataFrame({'label':labels,'batch':batches}).drop_duplicates()
    counts=df.groupby('label',observed=False)['batch'].count()
    if threshold is None: threshold=int(counts.min())
    return counts[counts<=threshold].index.tolist(),{str(k):int(v) for k,v in counts.items()},int(threshold)

def scaled_macro(samples,labels,selected):
    values=[]
    for lab in selected:
        values.append(float(np.mean(samples[np.asarray(labels)==lab])))
    return float((np.mean(values)+1)/2),{str(lab):float((np.mean(samples[np.asarray(labels)==lab])+1)/2) for lab in selected}

def main():
    set_config(working_memory=512)
    OUT.mkdir(parents=True,exist_ok=True); records=fetch()
    label_paths=[INPUT/'cty1.csv',INPUT/'cty2.csv',INPUT/'cty3.csv']
    cell_codes,cell_names,categories=read_labels(label_paths); batches=read_batches(label_paths)
    x=read_embedding(INPUT/'embedding.h5'); clusters=read_cluster(INPUT/'sinfonia_clustering.h5')
    if not (len(x)==len(cell_codes)==len(batches)==len(clusters)): raise ValueError((x.shape,len(cell_codes),len(batches),len(clusters)))
    # Use string biological names for transparent selection/output. Equality partitions are identical to global categorical codes.
    num=float(np.max(batches)+1); batch_count=len(np.unique(batches))
    released_cell_selected,cell_counts,_=selected_labels(cell_names,batches,num)
    default_cell_selected,_,default_threshold=selected_labels(cell_names,batches,None)
    released_cluster_selected,cluster_counts,_=selected_labels(clusters,batches,num)
    print('data',x.shape,'celltypes',len(np.unique(cell_names)),'clusters',len(np.unique(clusters)),'batches',batch_count,flush=True)
    print('default isolated celltypes',default_cell_selected,flush=True)
    cluster_samples=silhouette_samples(x,clusters,metric='euclidean')
    print('cluster silhouette complete',flush=True)
    cell_samples=silhouette_samples(x,cell_names,metric='euclidean')
    print('celltype silhouette complete',flush=True)
    ordinary={'released_cluster_ASW':float((np.mean(cluster_samples)+1)/2),'celltype_ASW':float((np.mean(cell_samples)+1)/2)}
    released_iasw,released_by_cluster=scaled_macro(cluster_samples,clusters,released_cluster_selected)
    label_only_iasw,label_only_by_cell=scaled_macro(cell_samples,cell_names,released_cell_selected)
    corrected_iasw,corrected_by_cell=scaled_macro(cell_samples,cell_names,default_cell_selected)
    result={'scope':'Released repository embedding demo reanalysis; not identified as a named original-paper run or corrected leaderboard.',
      'upstream_commit':COMMIT,'environment':{'python':platform.python_version(),'numpy':importlib.metadata.version('numpy'),'pandas':importlib.metadata.version('pandas'),'scikit-learn':importlib.metadata.version('scikit-learn'),'h5py':importlib.metadata.version('h5py')},
      'inputs':records,'dimensions':{'observations':len(x),'embedding_dimensions':int(x.shape[1]),'batches':batch_count,'celltypes':len(np.unique(cell_names)),'clusters':len(np.unique(clusters))},
      'thresholds':{'scMultiBench_num':num,'scib_default_threshold_for_celltypes':default_threshold,'released_threshold_celltypes_selected':released_cell_selected,'default_celltypes_selected':default_cell_selected,'celltype_batch_presence':cell_counts,'released_cluster_labels_selected':released_cluster_selected,'cluster_batch_presence':cluster_counts},
      'ordinary_ASW':ordinary,
      'iASW':{'released_cluster_labels_plus_threshold':released_iasw,'celltype_labels_with_released_threshold':label_only_iasw,'celltype_labels_with_scib_default_isolation':corrected_iasw,
              'released_per_cluster_scaled':released_by_cluster,'released_threshold_per_celltype_scaled':label_only_by_cell,'default_isolated_per_celltype_scaled':corrected_by_cell}}
    (OUT/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    pd.DataFrame({'celltype':cell_names,'batch':batches.astype(int),'celltype_silhouette_raw':cell_samples}).to_csv(OUT/'celltype_samples.csv.gz',index=False,compression='gzip')
    pd.DataFrame({'cluster':clusters,'batch':batches.astype(int),'cluster_silhouette_raw':cluster_samples}).to_csv(OUT/'cluster_samples.csv.gz',index=False,compression='gzip')
    print(json.dumps({k:result[k] for k in ('dimensions','thresholds','ordinary_ASW','iASW')},indent=2,ensure_ascii=False),flush=True)
    print('PASS: released demo ASW/iASW reanalysis complete.',flush=True)
if __name__=='__main__': main()
