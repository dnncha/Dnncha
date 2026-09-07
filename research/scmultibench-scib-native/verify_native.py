"""Native scib 1.1.5 checks for two scMultiBench metric defects.

This executes the real scib silhouette and isolated-label ASW functions on
synthetic AnnData. It source-verifies both scMultiBench and scib. It does not
rerun the original paper datasets or claim which scib version the authors used.
"""
from __future__ import annotations
import ast
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import platform
from urllib.request import Request, urlopen

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from scib.metrics.silhouette import silhouette
from scib.metrics.isolated_labels import get_isolated_labels, isolated_labels_asw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'
SCMULTI_COMMIT = '0c68f87d554a52e363dbfda2a9d1fa9538eeae9f'
SCIB_COMMIT = '59ae6eee5e611d9d3db067685ec96c28804e9127'  # v1.1.5
SOURCES = [
    ('scMultiBench', f'https://raw.githubusercontent.com/PYangLab/scMultiBench/{SCMULTI_COMMIT}/evaluation_pipelines/scib_metrics/scib_metrics.py', 'b8549d293d2a6eaef9af91bd7842dc68e15e9fcf'),
    ('scib-isolated', f'https://raw.githubusercontent.com/theislab/scib/{SCIB_COMMIT}/scib/metrics/isolated_labels.py', '2e8258ab79f972cd983f902f20e3cb247db820cc'),
    ('scib-silhouette', f'https://raw.githubusercontent.com/theislab/scib/{SCIB_COMMIT}/scib/metrics/silhouette.py', '8d44b3aa8c2e90e3e1792db35efc7ca4fdc25a7a'),
]


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()


def fetch_sources():
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    texts = {}
    for name, url, expected in SOURCES:
        with urlopen(Request(url, headers={'User-Agent':'CheerfulDuck-scientific-code-audit'}), timeout=40) as response:
            raw = response.read(200_001)
        if len(raw) > 200_000:
            raise ValueError('Unexpected source size: ' + name)
        actual = git_blob(raw)
        if actual != expected:
            raise ValueError(f'{name} Git blob mismatch: {actual} != {expected}')
        (OUT / f'{name}.py').write_bytes(raw)
        records.append({'name':name,'url':url,'bytes':len(raw),'git_blob_sha1':actual,
                        'sha256':hashlib.sha256(raw).hexdigest()})
        texts[name] = raw.decode()
    return records, texts


def function_ast(text, name):
    nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    return ast.dump(nodes[0], include_attributes=False)


def installed_source_matches(texts):
    # Verify the wheel/imported functions are the same definitions as v1.1.5.
    installed_iso = inspect.getsource(get_isolated_labels)
    installed_sil = inspect.getsource(silhouette)
    assert function_ast(installed_iso, 'get_isolated_labels') == function_ast(texts['scib-isolated'], 'get_isolated_labels')
    assert function_ast(installed_sil, 'silhouette') == function_ast(texts['scib-silhouette'], 'silhouette')


def check_scMultiBench_calls(text):
    tree = ast.parse(text)
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            try:
                fn = ast.unparse(node.func)
            except Exception:
                continue
            if fn.endswith('isolated_labels_asw') or fn.endswith('isolated_labels_f1') or fn.endswith('silhouette'):
                calls.append(ast.unparse(node))
    joined = '\n'.join(calls)
    assert 'label_key="cluster"' in joined
    assert 'isolated_labels_asw' in joined and 'iso_threshold=num' in joined
    assert 'isolated_labels_f1' in joined and 'iso_threshold=num' in joined
    return calls


def make_adata(x, labels, batches, clusters=None):
    a = ad.AnnData(X=np.asarray(x).copy())
    a.obsm['X_emb'] = np.asarray(x).copy()
    a.obs['celltype'] = pd.Categorical(labels)
    a.obs['batch'] = pd.Categorical([str(v) for v in batches])
    if clusters is not None:
        a.obs['cluster'] = pd.Categorical(clusters)
    return a


def silhouette_fixture():
    n = 120
    truth = np.repeat([0,1], n//2)
    technical_partition = np.tile([0,1], n//2)
    rng = np.random.default_rng(0)
    biological = rng.normal(0,.35,(n,2)) + np.column_stack((truth*4.-2., np.zeros(n)))
    technical = rng.normal(0,.08,(n,2)) + np.column_stack((technical_partition*20.-10., np.zeros(n)))
    rows = {}
    for name, x in [('biological', biological), ('technical', technical)]:
        clusters = KMeans(n_clusters=2, random_state=0, n_init=10).fit_predict(x)
        a = make_adata(x, truth, np.ones(n), clusters)
        released = float(silhouette(a, label_key='cluster', embed='X_emb'))
        corrected = float(silhouette(a, label_key='celltype', embed='X_emb'))
        rows[name] = {'released_cluster_asw':released,'celltype_asw':corrected}
    assert rows['technical']['released_cluster_asw'] > rows['biological']['released_cluster_asw']
    assert rows['technical']['celltype_asw'] < rows['biological']['celltype_asw']
    return rows


def isolation_fixture():
    labels=[]; batches=[]
    for batch in (1,2,3):
        for lab in ('C1','C2','C3','C4'):
            labels += [lab]*25; batches += [batch]*25
    labels += ['R']*25; batches += [1]*25
    labels=np.asarray(labels); batches=np.asarray(batches)
    means_a={'R':(10,0),'C1':(-.15,0),'C2':(.15,0),'C3':(0,.15),'C4':(0,-.15)}
    means_b={'R':(-7,0),'C1':(-7,0),'C2':(7,0),'C3':(0,7),'C4':(0,-7)}
    def build(means, seed, sigma):
        rng=np.random.default_rng(seed); x=np.zeros((len(labels),2))
        for lab, mu in means.items():
            idx=np.flatnonzero(labels==lab)
            x[idx]=rng.normal(0,sigma,(len(idx),2))+np.asarray(mu)
        return make_adata(x,labels,batches)
    a=build(means_a,0,.8); b=build(means_b,1,.5)
    # scMultiBench numbers batches 1..B then sets num=max(batch)+1.
    num=float(np.max(batches)+1)
    assert num == 4
    default_labels=get_isolated_labels(a,'celltype','batch',None,False)
    released_labels=get_isolated_labels(a,'celltype','batch',num,False)
    assert default_labels == ['R'], default_labels
    assert set(released_labels) == {'C1','C2','C3','C4','R'}, released_labels
    rows={}
    for name, obj in [('A_isolated_label_preserved',a),('B_common_labels_preserved',b)]:
        default=float(isolated_labels_asw(obj,label_key='celltype',batch_key='batch',embed='X_emb',iso_threshold=None,verbose=False))
        released=float(isolated_labels_asw(obj,label_key='celltype',batch_key='batch',embed='X_emb',iso_threshold=num,verbose=False))
        rows[name]={'default_isolated_policy_iASW':default,'released_threshold_iASW':released}
    assert rows['A_isolated_label_preserved']['default_isolated_policy_iASW'] > rows['B_common_labels_preserved']['default_isolated_policy_iASW']
    assert rows['A_isolated_label_preserved']['released_threshold_iASW'] < rows['B_common_labels_preserved']['released_threshold_iASW']
    return {'batch_count':3,'scMultiBench_num':num,'default_selected_labels':default_labels,
            'released_selected_labels':released_labels,'candidates':rows}


def main():
    version=importlib.metadata.version('scib')
    assert version == '1.1.5', version
    sources,texts=fetch_sources()
    installed_source_matches(texts)
    calls=check_scMultiBench_calls(texts['scMultiBench'])
    result={'scope':'Synthetic native scib/AnnData verification; no original publication dataset or leaderboard rerun.',
            'environment':{'python':platform.python_version(),'scib':version,'anndata':importlib.metadata.version('anndata'),
                           'numpy':importlib.metadata.version('numpy'),'pandas':importlib.metadata.version('pandas'),
                           'scikit-learn':importlib.metadata.version('scikit-learn')},
            'sources':sources,'scmultibench_metric_calls':calls,
            'silhouette_label_source':silhouette_fixture(),'isolated_label_threshold':isolation_fixture()}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    print('PASS: native scib reproduces both label-source and isolation-threshold preference reversals.')

if __name__=='__main__':
    main()
