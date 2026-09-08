# Category metadata can reverse scMultiBench's spatial matching score

Donncha O'Toole · Cheerful Duck · 7 September 2026

The released spatial-registration PAA scorer compares categorical integer codes from different slices without giving those codes a shared biological meaning. Changing one slice's category order can turn a perfect label match into a score of zero and a completely wrong match into a score of one, while the observation labels, coordinates, expression data and test couplings stay unchanged.

The defect has now been source-verified in **five released evaluator paths**: PASTE pairwise, PASTE center, PASTE2, GPSA and SPIRAL. [Upstream issue #5](https://github.com/PYangLab/scMultiBench/issues/5) · [latest passing run](https://github.com/dnncha/Dnncha/actions/runs/34141189095) · [primary native test](verify_native.py) · [GPSA/SPIRAL propagation test](verify_additional_paths.py)

## The error

At scMultiBench commit `0c68f87d554a52e363dbfda2a9d1fa9538eeae9f`, each affected path contains the same helper:

```python
binary_matrix = np.zeros((slice.n_obs, n_categories))
for idx, cat in enumerate(slice.obs['Ground_Truth'].cat.codes):
    binary_matrix[idx, cat] = 1
```

The two slices are encoded independently. The scorer then constructs a match matrix from the one-hot columns and weights it by an alignment/coupling plan. Code `0` can mean A in one slice and B in another, but the dot product treats those columns as the same class. Setting the matrix width to the number of distinct label names does not establish a common code-to-label mapping.

## Executed counterexample

Both slices contain the same four labels `[A, A, B, B]`. The reference stores categories as `[A, B]`. The query initially does the same; its category metadata is then reordered to `[B, A]` without changing the value of a single observation label.

Two fixed synthetic couplings are evaluated: one pairs every observation with the same biological type, while the other pairs every A with B and every B with A. Both have unit total mass and uniform marginals.

| Query category metadata | Correct-label coupling | Wrong-label coupling |
|---|---:|---:|
| `[A, B]` | 1.0 | 0.0 |
| `[B, A]` | 0.0 | 1.0 |
| Shared vocabulary applied before encoding | 1.0 | 0.0 |

The score preference reverses from correct to completely wrong solely because of categorical storage metadata. These are constructed coupling matrices, not alignments produced by a benchmarked solver.

A second fixture needs no deliberate category reordering. The reference contains `[A,A,B,B]`, the query `[B,B,C,C]`, and each slice uses its ordinary local category vocabulary. Their local integer codes coincide, so an identity coupling receives **1.0 even though none of the paired biological labels agree**. A shared `[A,B,C]` vocabulary returns 0.0.

## Five source-verified paths

The tests download the complete files at the immutable upstream commit and reject a Git-blob mismatch before extracting the original helper and match/weighted-sum arithmetic.

| Released evaluator | Git blob SHA | Verified result |
|---|---|---|
| `PASTE_pairwise.py` | `61c65fda0f3b6cd58d7f3382847e4e7b9789cfe0` | 1/0 → 0/1 reversal |
| `PASTE_center.py` | `58f62baee12cf033642da6ee82caa2574cf5cd2b` | 1/0 → 0/1 reversal |
| `PASTE2_metric.py` | `1e2df97ed73a368cf6a75073a190275f56952e5c` | 1/0 → 0/1 reversal |
| `gpsa_metric.py` | `ff7a7530010769f3a16dedd732d58204f63c18fa` | 1/0 → 0/1 reversal |
| `SPIRAL_metric.py` | `e6caa02c3a59c3f1e5bbcdd9b0de55b0b274be6b` | 1/0 → 0/1 reversal |

The first three paths were additionally checked through native `.h5ad` write/read persistence, all 36 independent category-order combinations for three classes and 100 seeded coupling/label cases per implementation. The corrected shared-vocabulary arithmetic agrees with a separate oracle that compares the actual biological label values.

GPSA and SPIRAL use the same one-hot helper and matching arithmetic but call the synthetic coupling variable `ot_plan` rather than `pi`; the propagation adapter supplies the identical fixed test matrix under the upstream variable name. The first propagation attempt failed because the adapter assumed `pi`; the corrected rerun passes. No scientific result from that failed harness attempt is counted.

Environment for the native tests: Python 3.11.16, AnnData 0.10.9, NumPy 1.26.4, pandas 2.2.3, SciPy 1.14.1 and h5py 3.16.0. These are audit dependencies, not a reconstruction of the publication environment.

Run `34141189095` passed at branch head `1dbb745af1fa23dbdb46049e4c7febca75604c33`. Its ten-file evidence archive contains all five complete source snapshots represented across the primary and propagation outputs, result records, dependency versions and logs. The archive was downloaded and independently checksum-verified as SHA-256 `2ff2452480fcb94f72ea107370d0be4a2295780fcb78dfa96053e8e1f91781f4` (artifact `10025958278`).

## Correction and publication scope

Use a common biological-label vocabulary for every slice before constructing one-hot matrices, including a center slice where applicable, or build the match matrix directly from equality of the actual label values. Missing labels need an explicit policy rather than silently using categorical code `-1` as an array index.

The tested correction re-encodes copies of the slices against a shared vocabulary and then executes the unchanged upstream scoring arithmetic. It leaves the coupling and observations unchanged. This is a tested correction to the encoding step, not a claim that every original benchmark run was affected.

The associated paper is [Multitask benchmarking of single-cell multimodal omics integration methods](https://www.nature.com/articles/s41592-025-02856-3), Nature Methods (2025), DOI `10.1038/s41592-025-02856-3`.

The outstanding publication question is whether the categorical vocabularies and orders happened to be identical for every slice used in each original spatial-registration comparison. Inputs satisfying that condition avoid this particular failure even though the scorer does not enforce it. Original category metadata and coupling matrices, or reproducible original inputs, are needed to measure affected publication scores. No named method ranking or recommendation is claimed to have changed.

## Reproduce

```sh
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.14.1 anndata==0.10.9 'zarr<3'
python research/scmultibench-paa-categories/verify_native.py
python research/scmultibench-paa-categories/verify_additional_paths.py
```

[All scientific audit reports](../)
