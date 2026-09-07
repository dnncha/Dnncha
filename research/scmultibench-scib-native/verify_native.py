"""Native scib 1.1.5 checks for two scMultiBench metric defects.

Executes real scib silhouette and isolated-label ASW functions on synthetic
AnnData. Sources are Git-blob verified. This is not an original-paper rerun and
scMultiBench does not pin the exact scib version used for publication.
"""
from __future__ import annotations
import ast, hashlib, importlib.metadata, inspect, json, platform
from pathlib import Path
from urllib.request import Request, urlopen
import anndata as ad
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from scib.metrics.silhouette import silhouette
from scib.metrics.isolated_labels import get_isolated_labels, isolated_labels_asw

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'results'
SCMULTI='0c68f87d554a52e363dbfda2a9d1fa9538eeae9f'
SCIB='59ae6eee5e611d9d3db067685ec96c28804e9127'  # v1.1.5
SOURCES=[
 ('scMultiBench',f'https://raw.githubusercontent.com/PYangLab/scMultiBench/{SCMULTI}/evaluation_pipelines/scib_metrics/scib_metrics.py','b8549d293d2a6eaef9af91bd7842dc68e15e9fcf'),
 ('scib-isolated',f'https://raw.githubusercontent.com/theislab/scib/{SCIB}/scib/metrics/isolated_labels.py','2e8258ab79f972cd983f902f20e3cb247db820cc'),
 ('scib-silhouette',f'https://raw.githubusercontent.com/theislab/scib/{SCIB}/scib/metrics/silhouette.py','8d44b3aa8c2e90e3e1792db35efc7ca4fdc25a7a')]

def blob(raw): return hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
def fetch_sources():
    OUT.mkdir(parents=True,exist_ok=True); rec=[]; texts={}
    for name,url,expected in SOURCES:
        with urlopen(Request(url,headers={'User-Agent':'CheerfulDuck-scientific-code-audit'}),timeout=40) as r: raw=r.read(200001)
        assert len(raw)<=200000 and blob(raw)==expected,(name,blob(raw),expected)
        (OUT/f'{name}.py').write_bytes(raw); texts[name]=raw.decode()
        rec.append({'name':name,'url':url,'bytes':len(raw),'git_blob_sha1':blob(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    return rec,texts

def fn_ast(text,name):
    nodes=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name]
    assert len(nodes)==1
    return ast.dump(nodes[0],include_attributes=False)

def check_installed(texts):
    assert fn_ast(inspect.getsource(get_isolated_labels),'get_isolated_labels')==fn_ast(texts['scib-isolated'],'get_isolated_labels')
    assert fn_ast(inspect.getsource(silhouette),'silhouette')==fn_ast(texts['scib-silhouette'],'silhouette')

def check_calls(text):
    found={'silhouette_cluster':False,'iasw_num':False,'if1_num':False}; calls=[]
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node,ast.Call): continue
        name=ast.unparse(node.func); kw={x.arg:x.value for x in node.keywords if x.arg}
        if name.endswith(('silhouette','isolated_labels_asw','isolated_labels_f1')): calls.append(ast.unparse(node))
        label=kw.get('label_key'); threshold=kw.get('iso_threshold')
        if name.endswith('silhouette') and isinstance(label,ast.Constant) and label.value=='cluster': found['silhouette_cluster']=True
        if name.endswith('isolated_labels_asw') and isinstance(threshold,ast.Name) and threshold.id=='num': found['iasw_num']=True
        if name.endswith('isolated_labels_f1') and isinstance(threshold,ast.Name) and threshold.id=='num': found['if1_num']=True
    assert all(found.values()),found
    return {'found':found,'calls':calls}

def make(x,labels,batches,clusters=None):
    a=ad.AnnData(X=np.asarray(x).copy()); a.obsm['X_emb']=np.asarray(x).copy()
    a.obs['celltype']=pd.Categorical(labels); a.obs['batch']=pd.Categorical([str(x) for x in batches])
    if clusters is not None: a.obs['cluster']=pd.Categorical(clusters)
    return a

def silhouette_test():
    n=120; truth=np.repeat([0,1],n//2); technical_partition=np.tile([0,1],n//2); rng=np.random.default_rng(0)
    bio=rng.normal(0,.35,(n,2))+np.column_stack((truth*4.-2.,np.zeros(n)))
    tech=rng.normal(0,.08,(n,2))+np.column_stack((technical_partition*20.-10.,np.zeros(n)))
    out={}
    for name,x in [('biological',bio),('technical',tech)]:
        clusters=KMeans(n_clusters=2,random_state=0,n_init=10).fit_predict(x); a=make(x,truth,np.ones(n),clusters)
        out[name]={'released_cluster_asw':float(silhouette(a,'cluster','X_emb')),
                   'celltype_asw':float(silhouette(a,'celltype','X_emb'))}
    assert out['technical']['released_cluster_asw']>out['biological']['released_cluster_asw']
    assert out['technical']['celltype_asw']<out['biological']['celltype_asw']
    return out

def isolation_test():
    labels=[]; batches=[]
    for b in (1,2,3):
        for lab in ('C1','C2','C3','C4'): labels += [lab]*25; batches += [b]*25
    labels += ['R']*25; batches += [1]*25; labels=np.asarray(labels); batches=np.asarray(batches)
    meansA={'R':(10,0),'C1':(-.15,0),'C2':(.15,0),'C3':(0,.15),'C4':(0,-.15)}
    meansB={'R':(-7,0),'C1':(-7,0),'C2':(7,0),'C3':(0,7),'C4':(0,-7)}
    def build(means,seed,sigma):
        rng=np.random.default_rng(seed); x=np.zeros((len(labels),2))
        for lab,mu in means.items():
            idx=np.flatnonzero(labels==lab); x[idx]=rng.normal(0,sigma,(len(idx),2))+np.asarray(mu)
        return make(x,labels,batches)
    A=build(meansA,0,.8); B=build(meansB,1,.5); num=float(np.max(batches)+1); assert num==4
    default=get_isolated_labels(A,'celltype','batch',None,False); released=get_isolated_labels(A,'celltype','batch',num,False)
    assert default==['R'] and set(released)=={'C1','C2','C3','C4','R'}
    rows={}
    for name,obj in [('A_isolated_label_preserved',A),('B_common_labels_preserved',B)]:
        rows[name]={'default_isolated_policy_iASW':float(isolated_labels_asw(obj,'celltype','batch','X_emb',None,True,False)),
                    'released_threshold_iASW':float(isolated_labels_asw(obj,'celltype','batch','X_emb',num,True,False))}
    assert rows['A_isolated_label_preserved']['default_isolated_policy_iASW']>rows['B_common_labels_preserved']['default_isolated_policy_iASW']
    assert rows['A_isolated_label_preserved']['released_threshold_iASW']<rows['B_common_labels_preserved']['released_threshold_iASW']
    return {'batch_count':3,'scMultiBench_num':num,'default_selected_labels':default,'released_selected_labels':released,'candidates':rows}

def main():
    assert importlib.metadata.version('scib')=='1.1.5'
    sources,texts=fetch_sources(); check_installed(texts)
    result={'scope':'Synthetic native scib/AnnData verification; no original publication dataset or leaderboard rerun.',
      'environment':{'python':platform.python_version(),'scib':importlib.metadata.version('scib'),'anndata':importlib.metadata.version('anndata'),'numpy':importlib.metadata.version('numpy'),'pandas':importlib.metadata.version('pandas'),'scikit-learn':importlib.metadata.version('scikit-learn')},
      'sources':sources,'source_call_checks':check_calls(texts['scMultiBench']),
      'silhouette_label_source':silhouette_test(),'isolated_label_threshold':isolation_test()}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
    print('PASS: native scib reproduces both label-source and isolation-threshold preference reversals.')
if __name__=='__main__': main()
