# Category metadata can reverse scMultiBench's spatial matching score

Donncha O'Toole · Cheerful Duck · 7 September 2026

The released spatial-registration PAA scorer compares categorical integer codes from different slices without giving those codes a shared meaning. Changing one slice's category order can turn a perfect label match into a score of zero, and a completely wrong match into a score of one. The observation labels, coordinates, expression data and test couplings stay unchanged.

[Successful native execution](https://github.com/dnncha/Dnncha/actions/runs/34129212337) · [executable source-verified test](verify_native.py) · [full numerical result](verified-result.json)

## The error

At scMultiBench commit `0c68f87d554a52e363dbfda2a9d1fa9538eeae9f`, `create_binary_matrix` contains:

```python
binary_matrix = np.zeros((slice.n_obs, n_categories))
for idx, cat in enumerate(slice.obs['Ground_Truth'].cat.codes):
    binary_matrix[idx, cat] = 1
```

The caller builds a matrix for each slice independently, then calculates:

```python
matched_pairs = np.dot(binary_matrix_i, binary_matrix_j.T)
total_accuracy += np.sum(pi * matched_pairs)
```

Code 0 can mean A in one slice and B in the other. The dot product treats them as a match anyway. Setting the matrix width to the number of distinct biological labels does not establish a common code-to-label mapping.

## Executed counterexample

Both slices have four observations, with labels `[A, A, B, B]`. The reference stores its categories as `[A, B]`. The query initially does the same; its category metadata is then reordered to `[B, A]`, without changing any observation's label.

Two fixed test coupling matrices are evaluated. One pairs each observation with its identically labelled counterpart. The other pairs every A with a B and every B with an A. Both have unit total mass and uniform marginals.

| Query category metadata | Correct-label coupling | Wrong-label coupling |
|---|---:|---:|
| `[A, B]` | 1.0 | 0.0 |
| `[B, A]` | 0.0 | 1.0 |
| Shared vocabulary applied to both slices | 1.0 | 0.0 |

This is a complete reversal of the two test couplings' PAA scores, not a demonstrated reversal of the paper's method rankings. No alignment algorithm generated these couplings.

A second case does not require deliberately reordering categories. The reference labels are `[A, A, B, B]`, while the query labels are `[B, B, C, C]`. Each slice uses its own alphabetically ordered categories. For an identity coupling, the original arithmetic reports 1.0 although none of the paired biological labels agree. Giving both slices the shared vocabulary `[A, B, C]` returns 0.0. Different observed label sets therefore matter as well as explicit metadata reordering.

## Native checks

The test downloaded and verified three complete files at the immutable upstream commit, then executed each original `create_binary_matrix` function and the original match-matrix and weighted-sum statements from `calculate_PAA`:

| File under `evaluation_pipelines/spatial_registration/` | Bytes | Git blob SHA |
|---|---:|---|
| `PASTE_pairwise.py` | 11,447 | `61c65fda0f3b6cd58d7f3382847e4e7b9789cfe0` |
| `PASTE_center.py` | 11,434 | `58f62baee12cf033642da6ee82caa2574cf5cd2b` |
| `PASTE2_metric.py` | 8,926 | `1e2df97ed73a368cf6a75073a190275f56952e5c` |

All three reproduce the primary table and the different-label-set failure. For each file, the test also verifies a native `.h5ad` write/read round trip, all 36 independent category-order combinations for three classes, and 100 seeded coupling/label cases. Shared-vocabulary results agree with a separate oracle that compares the actual label values directly.

The round trip preserves the failure; it is not an artefact of an in-memory stand-in. The run uses real AnnData 0.10.9, NumPy 1.26.4, pandas 2.2.3, SciPy 1.14.1 and h5py 3.16.0 on Python 3.11.16. These are audit dependencies, not the paper's reconstructed environment.

Only the listed functions/statements were executed. The full command-line pipelines, alignment solvers, center-specific averaging and original publication datasets were not run. This deliberately isolates label matching from alignment quality. The original source files remain unchanged; the correction standardizes category metadata on copies of the input objects.

Run `34129212337` passed at research-code commit `fde70536c658b11459860e91d96f11fb1da2b051`. Its evidence archive contains all three complete source snapshots, full results, dependency versions and the execution log. The archive was downloaded and independently checksum-verified: SHA-256 `3326118e9744748562710ce331f1e83325aaaf86630c2bb5c450f5e515e67617`. Artifact ID: `10021365079`. The result JSON is committed here so the findings do not depend on CI artifact retention.

## Correction and publication scope

Use a common biological-label vocabulary for all slices before constructing one-hot matrices, including the center when evaluating center-to-slice couplings. Alternatively, build the match matrix from equality of the actual label values. Missing labels require an explicit policy rather than silently assigning their negative category code to a column.

The minimal correction tested here constructs a shared vocabulary, re-encodes both slices against it, and then executes the unchanged upstream helper and scoring statements. It leaves the coupling matrix and all observations unchanged. It is a tested correction to the encoding step, not a submitted full-pipeline patch.

The associated publication is [Multitask benchmarking of single-cell multimodal omics integration methods](https://www.nature.com/articles/s41592-025-02856-3), Nature Methods (2025), DOI `10.1038/s41592-025-02856-3`. Source links: [PASTE pairwise](https://github.com/PYangLab/scMultiBench/blob/0c68f87d554a52e363dbfda2a9d1fa9538eeae9f/evaluation_pipelines/spatial_registration/PASTE_pairwise.py), [PASTE center](https://github.com/PYangLab/scMultiBench/blob/0c68f87d554a52e363dbfda2a9d1fa9538eeae9f/evaluation_pipelines/spatial_registration/PASTE_center.py), [PASTE2](https://github.com/PYangLab/scMultiBench/blob/0c68f87d554a52e363dbfda2a9d1fa9538eeae9f/evaluation_pipelines/spatial_registration/PASTE2_metric.py).

The outstanding publication question is whether every original input used exactly the same category vocabulary and order. If so, those particular runs may avoid this error. The inspected calculation does not enforce that condition. Original category metadata and couplings, or reproducible original inputs, are needed to measure affected publication scores. No particular published method result or recommendation is claimed to have changed.

## Reproduce

Use an isolated Python 3.11 environment:

```sh
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.14.1 anndata==0.10.9 'zarr<3'
python research/scmultibench-paa-categories/verify_native.py
```

The script fetches the three pinned source files and refuses any checksum mismatch. It does not train models or download publication datasets.

[All scientific audit reports](../)
