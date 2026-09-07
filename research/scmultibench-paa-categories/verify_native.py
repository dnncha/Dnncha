"""Test scMultiBench PAA label matching with real AnnData and pinned source.

Only categorical metadata is changed in the primary comparison. Couplings are
explicit synthetic inputs, not outputs of an alignment algorithm. No solver,
full benchmark CLI or original publication dataset is executed.
"""
from __future__ import annotations
import ast
import hashlib
import importlib.metadata
import itertools
import json
from pathlib import Path
import platform
import tempfile
from urllib.request import Request, urlopen

import anndata as ad
import numpy as np
import pandas as pd

COMMIT = '0c68f87d554a52e363dbfda2a9d1fa9538eeae9f'
SOURCES = {
    'PASTE_pairwise.py': '61c65fda0f3b6cd58d7f3382847e4e7b9789cfe0',
    'PASTE_center.py': '58f62baee12cf033642da6ee82caa2574cf5cd2b',
    'PASTE2_metric.py': '1e2df97ed73a368cf6a75073a190275f56952e5c',
}
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results'


def load_source(name, expected):
    url = f'https://raw.githubusercontent.com/PYangLab/scMultiBench/{COMMIT}/evaluation_pipelines/spatial_registration/{name}'
    path = OUT / 'source' / name
    if path.exists():
        raw = path.read_bytes()
    else:
        with urlopen(Request(url, headers={'User-Agent': 'CheerfulDuck-scientific-code-audit'}), timeout=40) as response:
            raw = response.read(100_001)
    if len(raw) > 100_000:
        raise ValueError('Unexpected source size')
    actual = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if actual != expected:
        raise ValueError(f'Wrong source: {name}: {actual}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    tree = ast.parse(raw)
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    helper = functions['create_binary_matrix']
    calculator = functions['calculate_PAA']
    matching = [n for n in ast.walk(calculator) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'matched_pairs' for t in n.targets)]
    additions = [n for n in ast.walk(calculator) if isinstance(n, ast.AugAssign)
                 and isinstance(n.target, ast.Name) and n.target.id == 'total_accuracy']
    assert len(matching) == len(additions) == 1
    ns = {'np': np}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), name, 'exec'), ns)
    statements = compile(ast.Module(body=[matching[0], additions[0]], type_ignores=[]), name, 'exec')
    provenance = {'file': name, 'url': url, 'bytes': len(raw), 'git_blob_sha1': actual,
                  'sha256': hashlib.sha256(raw).hexdigest(),
                  'helper_ast_sha256': hashlib.sha256(ast.dump(helper, include_attributes=False).encode()).hexdigest()}
    return ns['create_binary_matrix'], statements, provenance


def make_slice(labels, categories):
    n = len(labels)
    obs = pd.DataFrame({'Ground_Truth': pd.Categorical(labels, categories=categories)},
                       index=[f'cell_{i}' for i in range(n)])
    a = ad.AnnData(X=np.ones((n, 2)), obs=obs)
    a.obsm['spatial'] = np.column_stack([np.arange(n), np.zeros(n)])
    return a


def label_values(a):
    return a.obs['Ground_Truth'].astype(object).to_numpy()


def semantic_score(a, b, pi):
    # Independent oracle using biological names, not integer storage codes.
    return float(sum(pi[i, j] for i, x in enumerate(label_values(a))
                     for j, y in enumerate(label_values(b)) if x == y))


def released_score(helper, statements, a, b, pi):
    categories = set(label_values(a)) | set(label_values(b))
    ns = {'np': np, 'binary_matrix_i': helper(a, len(categories)),
          'binary_matrix_j': helper(b, len(categories)), 'pi': pi, 'total_accuracy': 0.0}
    exec(statements, ns)
    return float(ns['total_accuracy'])


def shared_vocabulary(a, b):
    if a.obs.Ground_Truth.isna().any() or b.obs.Ground_Truth.isna().any():
        raise ValueError('Missing biological labels need an explicit policy')
    categories = sorted(set(label_values(a)) | set(label_values(b)))
    copies = [a.copy(), b.copy()]
    for c in copies:
        c.obs['Ground_Truth'] = pd.Categorical(label_values(c), categories=categories)
    return copies


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    output = {'upstream_commit': COMMIT,
              'scope': 'Native AnnData synthetic label-matching tests; no alignment solver or original publication rerun.',
              'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p)
                              for p in ('anndata', 'numpy', 'pandas', 'scipy', 'h5py')}}, 'implementations': []}
    for name, blob in SOURCES.items():
        helper, statements, provenance = load_source(name, blob)
        a = make_slice(['A','A','B','B'], ['A','B'])
        b = make_slice(['A','A','B','B'], ['A','B'])
        reordered = b.copy()
        reordered.obs['Ground_Truth'] = reordered.obs.Ground_Truth.cat.reorder_categories(['B','A'])
        np.testing.assert_array_equal(label_values(b), label_values(reordered))
        np.testing.assert_array_equal(b.X, reordered.X)
        np.testing.assert_array_equal(b.obsm['spatial'], reordered.obsm['spatial'])
        good = np.eye(4) / 4
        bad = np.eye(4)[:, [2,3,0,1]] / 4
        primary = {}
        for label, query in [('same_category_order', b), ('reordered_categories', reordered)]:
            original = [released_score(helper, statements, a, query, pi) for pi in (good, bad)]
            fixed_a, fixed_b = shared_vocabulary(a, query)
            fixed = [released_score(helper, statements, fixed_a, fixed_b, pi) for pi in (good, bad)]
            oracle = [semantic_score(a, query, pi) for pi in (good, bad)]
            np.testing.assert_allclose(fixed, [1,0], atol=1e-15)
            np.testing.assert_allclose(fixed, oracle, atol=1e-15)
            primary[label] = {'original_good_bad': original, 'shared_vocabulary_good_bad': fixed}
        np.testing.assert_allclose(primary['same_category_order']['original_good_bad'], [1,0])
        np.testing.assert_allclose(primary['reordered_categories']['original_good_bad'], [0,1])
        # This survives native h5ad storage, not only an in-memory pandas object.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'query.h5ad'
            reordered.write_h5ad(p)
            restored = ad.read_h5ad(p)
            np.testing.assert_array_equal(label_values(restored), label_values(b))
            np.testing.assert_allclose(released_score(helper, statements, a, restored, good), 0)
        # Different observed label sets produce the same problem even with sorted categories.
        other = make_slice(['B','B','C','C'], ['B','C'])
        missing_set_original = released_score(helper, statements, a, other, good)
        fa, fb = shared_vocabulary(a, other)
        missing_set_fixed = released_score(helper, statements, fa, fb, good)
        np.testing.assert_allclose([missing_set_original, missing_set_fixed], [1,0])
        # Exhaust all independent category orders for three categories.
        checks = 0
        labels = ['A','B','C','A','B','C']
        for p1 in itertools.permutations(['A','B','C']):
            for p2 in itertools.permutations(['A','B','C']):
                left, right = make_slice(labels, p1), make_slice(labels, p2)
                pi = np.eye(6)/6
                fa, fb = shared_vocabulary(left, right)
                np.testing.assert_allclose(released_score(helper, statements, fa, fb, pi), semantic_score(left, right, pi))
                checks += 1
        random_checks = 0
        for seed in range(100):
            rng = np.random.default_rng(seed)
            lv = np.array(['A','B','C'] * 4)
            rv = lv[rng.permutation(12)]
            left = make_slice(lv, rng.permutation(['A','B','C']))
            right = make_slice(rv, rng.permutation(['A','B','C']))
            pi = (np.eye(12) + np.eye(12)[:, rng.permutation(12)]) / 24
            fa, fb = shared_vocabulary(left, right)
            value = released_score(helper, statements, fa, fb, pi)
            np.testing.assert_allclose(value, semantic_score(left, right, pi), atol=1e-15)
            random_checks += 1
        output['implementations'].append({'source': provenance, 'primary': primary,
            'different_label_sets': {'original': missing_set_original, 'corrected': missing_set_fixed},
            'native_h5ad_roundtrip_passed': True, 'category_permutation_checks': checks,
            'random_coupling_checks': random_checks})
    path = OUT / 'result.json'
    path.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))
    print('PASS: category metadata alone reverses both PAA coupling preferences in all three released helpers.')

if __name__ == '__main__':
    main()
