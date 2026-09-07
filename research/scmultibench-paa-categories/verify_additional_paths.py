"""Extend the source-verified PAA category-code check to GPSA and SPIRAL.

Uses the tested helpers from verify_native.py and executes only the original
one-hot helper plus matching/weighted-sum statements. No alignment solver or
publication dataset is run. GPSA/SPIRAL call their coupling `ot_plan`, while
other paths call it `pi`; the adapter supplies the same synthetic matrix under
both names without changing the extracted arithmetic.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from verify_native import load_source, make_slice, label_values, shared_vocabulary, semantic_score

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'additional-results'
SOURCES = {
    'gpsa_metric.py': 'ff7a7530010769f3a16dedd732d58204f63c18fa',
    'SPIRAL_metric.py': 'e6caa02c3a59c3f1e5bbcdd9b0de55b0b274be6b',
}


def score(helper, statements, a, b, coupling):
    categories=set(label_values(a)) | set(label_values(b))
    ns={'np':np,'binary_matrix_i':helper(a,len(categories)),
        'binary_matrix_j':helper(b,len(categories)),
        'pi':coupling,'ot_plan':coupling,'total_accuracy':0.0}
    exec(statements,ns)
    return float(ns['total_accuracy'])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows=[]
    for name, blob in SOURCES.items():
        helper, statements, provenance = load_source(name, blob)
        a=make_slice(['A','A','B','B'], ['A','B'])
        b=make_slice(['A','A','B','B'], ['A','B'])
        reordered=b.copy()
        reordered.obs['Ground_Truth']=reordered.obs.Ground_Truth.cat.reorder_categories(['B','A'])
        np.testing.assert_array_equal(label_values(b),label_values(reordered))
        good=np.eye(4)/4
        bad=np.eye(4)[:,[2,3,0,1]]/4
        released_same=[score(helper,statements,a,b,pi) for pi in (good,bad)]
        released_reordered=[score(helper,statements,a,reordered,pi) for pi in (good,bad)]
        fa,fb=shared_vocabulary(a,reordered)
        fixed=[score(helper,statements,fa,fb,pi) for pi in (good,bad)]
        oracle=[semantic_score(a,reordered,pi) for pi in (good,bad)]
        np.testing.assert_allclose(released_same,[1,0],atol=1e-15)
        np.testing.assert_allclose(released_reordered,[0,1],atol=1e-15)
        np.testing.assert_allclose(fixed,[1,0],atol=1e-15)
        np.testing.assert_allclose(fixed,oracle,atol=1e-15)
        other=make_slice(['B','B','C','C'],['B','C'])
        wrong_identity=score(helper,statements,a,other,good)
        fa,fb=shared_vocabulary(a,other)
        corrected_identity=score(helper,statements,fa,fb,good)
        np.testing.assert_allclose([wrong_identity,corrected_identity],[1,0],atol=1e-15)
        rows.append({'source':provenance,'same_order_good_bad':released_same,
                     'reordered_good_bad':released_reordered,'shared_vocabulary_good_bad':fixed,
                     'different_label_sets_identity':{'original':wrong_identity,'corrected':corrected_identity}})
    result={'scope':'Additional source-path propagation check; synthetic couplings only, no alignment solver or publication rerun.',
            'implementations':rows}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    print('PASS: GPSA and SPIRAL copies reproduce the same category-code score reversal.')

if __name__=='__main__': main()
