"""Self-contained arithmetic reproduction of scMultiBench issue #4.

Uses the same fixture as the full AST-based audit. This compact script calls
sklearn directly; it is NOT the full scMultiBench pipeline or scib integration.
Run: python research/scmultibench-silhouette/minimal_reproducer.py
"""
from __future__ import annotations
import json
import platform
from pathlib import Path
import importlib.metadata
import numpy as np
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from threadpoolctl import threadpool_limits


def direct_asw(x, labels):
    d = cdist(x, x)
    values = []
    for i, label in enumerate(labels):
        own = np.flatnonzero(labels == label)
        own = own[own != i]
        if not len(own):
            values.append(0.)
            continue
        a = d[i, own].mean()
        b = min(d[i, labels == other].mean() for other in np.unique(labels) if other != label)
        values.append((b-a)/max(a,b) if max(a,b) else 0.)
    return float((np.mean(values)+1)/2)


def main():
    n = 120
    truth = np.repeat([0, 1], n//2)
    technical_partition = np.tile([0, 1], n//2)
    results = []
    with threadpool_limits(limits=1):
        for seed in range(30):
            rng = np.random.default_rng(seed)
            biological = rng.normal(0, .35, (n, 2)) + np.column_stack((truth*4.-2., np.zeros(n)))
            technical = rng.normal(0, .08, (n, 2)) + np.column_stack((technical_partition*20.-10., np.zeros(n)))
            row = {'seed': seed}
            for name, x in [('biological', biological), ('technical', technical)]:
                clusters = KMeans(n_clusters=2, random_state=0, n_init=10).fit_predict(x)
                released = float((silhouette_score(x, clusters)+1)/2)
                celltype = float((silhouette_score(x, truth)+1)/2)
                np.testing.assert_allclose(released, direct_asw(x, clusters), atol=1e-12, rtol=0)
                np.testing.assert_allclose(celltype, direct_asw(x, truth), atol=1e-12, rtol=0)
                row[name] = {'released_asw': released, 'celltype_asw': celltype,
                             'cluster_truth_ari': float(adjusted_rand_score(truth, clusters))}
            assert row['technical']['released_asw'] > row['biological']['released_asw']
            assert row['technical']['celltype_asw'] < row['biological']['celltype_asw']
            results.append(row)
    np.testing.assert_allclose(results[0]['biological']['released_asw'], .9192562199107217, atol=1e-9)
    np.testing.assert_allclose(results[0]['technical']['released_asw'], .9963883077703815, atol=1e-9)
    np.testing.assert_allclose(results[0]['technical']['celltype_asw'], .49180269950470734, atol=1e-9)
    output = {'scope': 'Synthetic ASW metric comparison, not original publication results.',
              'execution': 'Compact sklearn arithmetic reproduction, not full upstream pipeline.',
              'environment': {'python': platform.python_version(), **{p: importlib.metadata.version(p)
                  for p in ['numpy','scipy','scikit-learn','threadpoolctl']}},
              'seed_results': results, 'independent_formula_comparisons': 120}
    Path(__file__).with_name('minimal_results.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(results[0], indent=2))
    print('PASS: 30/30 synthetic ASW comparisons reverse; 120 independent formula checks.')


if __name__ == '__main__':
    main()
