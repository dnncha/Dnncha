"""Run from pinned SABench checkout, or pass --source upstream_excerpt.py.

Requires numpy, pandas and scipy. --native additionally requires anndata.
The default Slice adapter supplies data storage and boolean row selection only.
"""
import argparse
import ast
import hashlib
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

parser = argparse.ArgumentParser()
parser.add_argument('--source', default='Tutorial/SABench.py')
parser.add_argument('--native', action='store_true')
args = parser.parse_args()
raw = Path(args.source).read_bytes()
if Path(args.source).name == 'SABench.py':
    digest = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    assert digest == '72990d43138389d359caa1a0b378d5deff969bfd', digest
nodes = [n for n in ast.parse(raw).body
         if isinstance(n, ast.FunctionDef) and n.name == 'Overlap_accuracy']
assert len(nodes) == 1
ns = {'np': np, 'cKDTree': cKDTree}
exec(compile(ast.Module(body=nodes, type_ignores=[]), args.source, 'exec'), ns)
score = ns['Overlap_accuracy']
warnings.filterwarnings('ignore', category=FutureWarning, message='Series.__getitem__')

class Slice:
    def __init__(self, xy, labels, ids=None):
        self.obsm = {'spatial': np.asarray(xy).copy()}
        if ids is None:
            ids = [f'cell_{i}' for i in range(len(xy))]
        self.obs = pd.DataFrame({'Region': labels}, index=ids)
    def __getitem__(self, item):
        mask, columns = item
        assert columns == slice(None)
        selected = self.obs.loc[mask]
        return Slice(self.obsm['spatial'][mask], selected.Region.to_numpy(), selected.index)

factory = Slice
if args.native:
    import anndata
    def factory(xy, labels):
        a = anndata.AnnData(X=np.zeros((len(xy), 1)),
            obs=pd.DataFrame({'Region': labels}, index=[f'cell_{i}' for i in range(len(xy))]))
        a.obsm['spatial'] = np.asarray(xy).copy()
        return a

x = np.array([[-1.5,2.9],[-1.8,.5],[-.6,2.9],[.9,1.5],
 [2.7,-2.4],[-.7,2.0],[2.9,-.6],[-1.2,-1.8],
 [-2.9,-.3],[.5,-2.1],[-1.9,-1.1],[.4,-2.5]], dtype=float)
labels = np.array(['A', 'B'] * 6)
shifts = [np.array([1.3,.4]), np.array([-.4,1.1])]
expected = [[.75,.25],[1/3,.625]]
for angle, expected_scores in zip([0,45], expected):
    t = np.deg2rad(angle)
    r = np.array([[np.cos(t),-np.sin(t)],[np.sin(t),np.cos(t)]])
    values = []
    for shift in shifts:
        y = x + shift
        xr, yr = x @ r.T, y @ r.T
        d0 = np.linalg.norm(x[:,None,:] - y[None,:,:], axis=2)
        d1 = np.linalg.norm(xr[:,None,:] - yr[None,:,:], axis=2)
        np.testing.assert_allclose(d0, d1, atol=1e-12, rtol=1e-12)
        values.append(score(factory(xr,labels), factory(yr,labels), 'spatial'))
    np.testing.assert_allclose(values, expected_scores)
    print(angle, values)
print('PASS (native AnnData)' if args.native else 'PASS (explicit data-container adapter)')
