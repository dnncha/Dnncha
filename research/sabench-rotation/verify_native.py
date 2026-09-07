"""Verify the original SABench numerical functions with real AnnData.

Downloads two immutable public sources, checks their complete Git blobs, then
executes only Overlap_accuracy and Average_Accuracy. No notebook top-level jobs
are run. This is a synthetic regression, not a publication-dataset reanalysis.
"""
from __future__ import annotations
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import urllib.request
import warnings
import anndata as ad
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist

COMMIT = '54d4e17c6dff5eab7ad93fee2a9bd70385ac750b'
SOURCES = {'Tutorial/SABench.py': '72990d43138389d359caa1a0b378d5deff969bfd',
           'FeatureSimilarity/LandmarkBased.ipynb': 'a56f85286ae48d27799d78624e3b0a4e59f625f3'}
X = np.array([[-1.5,2.9],[-1.8,.5],[-.6,2.9],[.9,1.5],
 [2.7,-2.4],[-.7,2.0],[2.9,-.6],[-1.2,-1.8],
 [-2.9,-.3],[.5,-2.1],[-1.9,-1.1],[.4,-2.5]], dtype=float)
LABELS = np.array(['A','B']*6)
OUT = Path(__file__).resolve().parent / 'native-results'


def make_slice(x):
    a = ad.AnnData(X=np.zeros((len(x),1)),
        obs=pd.DataFrame({'Region': LABELS}, index=[f'cell_{i}' for i in range(len(x))]))
    a.obsm['spatial'] = x.copy()
    return a


def main():
    OUT.mkdir(exist_ok=True)
    warnings.filterwarnings('ignore',category=FutureWarning,message='Series.__getitem__')
    record = {'upstream_commit': COMMIT, 'scope': 'Synthetic native AnnData function execution; no original publication rankings.',
              'python': platform.python_version(), 'environment': {p: importlib.metadata.version(p)
              for p in ['numpy','scipy','pandas','anndata','h5py','zarr']}, 'sources': []}
    ast_versions = []
    for path, expected in SOURCES.items():
        url = f'https://raw.githubusercontent.com/Yunzhi-Yan/SABench/{COMMIT}/{path}'
        with urllib.request.urlopen(url,timeout=30) as response:
            raw = response.read(1_000_001)
        if len(raw)>1_000_000:
            raise ValueError('Unexpected source size')
        digest = hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
        if digest != expected:
            raise ValueError(f'Source hash mismatch for {path}: {digest}')
        target = OUT / path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        chunks = [''.join(c['source']) for c in json.loads(raw)['cells'] if c['cell_type']=='code'] if path.endswith('.ipynb') else [raw.decode()]
        nodes = {}
        for chunk in chunks:
            for node in ast.parse(chunk).body:
                if isinstance(node,ast.FunctionDef) and node.name in {'Overlap_accuracy','Average_Accuracy'}:
                    if node.name in nodes:
                        raise ValueError('Duplicate function definition')
                    nodes[node.name] = node
        assert set(nodes)=={'Overlap_accuracy','Average_Accuracy'}
        ast_versions.append(ast.dump(nodes['Overlap_accuracy'],include_attributes=False))
        ns = {'np':np,'cKDTree':cKDTree}
        exec(compile(ast.Module(body=list(nodes.values()),type_ignores=[]),path,'exec'),ns)
        rows = []
        for angle, expected_scores in [(0,[.75,.25]),(45,[1/3,.625])]:
            t = np.deg2rad(angle)
            r = np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
            scores = []
            for shift in [np.array([1.3,.4]),np.array([-.4,1.1])]:
                y = X+shift
                xr,yr = X@r.T,y@r.T
                np.testing.assert_allclose(cdist(X,y),cdist(xr,yr),atol=1e-12,rtol=1e-12)
                a,b = make_slice(xr),make_slice(yr)
                score = float(ns['Overlap_accuracy'](a,b,'spatial'))
                np.testing.assert_allclose(ns['Average_Accuracy']([a,b]),score)
                np.testing.assert_array_equal(a.obsm['spatial'],xr)
                np.testing.assert_array_equal(b.obsm['spatial'],yr)
                scores.append(score)
            np.testing.assert_allclose(scores,expected_scores,atol=1e-12,rtol=1e-12)
            rows.append({'angle':angle,'scores':scores})
        record['sources'].append({'path':path,'url':url,'bytes':len(raw),'git_blob_sha1':digest,
                                 'sha256':hashlib.sha256(raw).hexdigest(),'cases':rows})
    assert ast_versions[0]==ast_versions[1]
    record['matching_overlap_function_asts'] = True
    record['native_ann_data'] = True
    record['result'] = 'PASS'
    (OUT/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))
    print('PASS: both complete hash-verified source locations reproduce the reversal with actual AnnData.')


if __name__=='__main__':
    main()
