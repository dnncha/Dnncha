# scMultiBench's cell-type silhouette score uses predicted clusters

Donncha O'Toole · 7 September 2026 · Cheerful Duck

[Public upstream report: issue #4](https://github.com/PYangLab/scMultiBench/issues/4)

The embedding evaluator prints `ASW_cellType` but calculates it from predicted cluster labels, not the biological annotations it has already loaded. A constructed example makes the metric prefer compact technical groups with mixed cell types. Changing only the label source reverses that metric's preference.

This is a released-code/metric-definition mismatch. It is not an original-dataset reanalysis, corrected overall leaderboard or allegation of misconduct.

## Source and proposed change

Paper: Liu et al., [Multitask benchmarking of single-cell multimodal omics integration methods](https://www.nature.com/articles/s41592-025-02856-3), Nature Methods (2025), DOI `10.1038/s41592-025-02856-3`. Its Evaluation metrics section identifies average silhouette width by cell type.

Pinned repository: `PYangLab/scMultiBench`, commit `0c68f87d554a52e363dbfda2a9d1fa9538eeae9f`.

The complete 5,723-byte [embedding evaluator](https://github.com/PYangLab/scMultiBench/blob/0c68f87d554a52e363dbfda2a9d1fa9538eeae9f/evaluation_pipelines/scib_metrics/scib_metrics.py) was recovered and verified against Git blob `b8549d293d2a6eaef9af91bd7842dc68e15e9fcf`. Its ordinary and isolated-label silhouette calls both pass `label_key="cluster"`. `celltype` contains the biological labels; `cluster` is loaded from the supplied `cluster_leiden` dataset. Other metrics in the same file use `celltype` as their biological reference.

The scib function uses the labels supplied; it does not substitute cell types internally. Internal cluster silhouette is a valid statistic, but it is not the stated biological-label silhouette. The authors have been asked to confirm the intended quantity.

The proposed two-line patch changes only the two `label_key="cluster"` arguments to `label_key="celltype"`. It leaves other metrics, clustering settings and isolation policy unchanged. It applied and reversed byte-for-byte in the local check.

## Executed result

Both candidates contain the same 120 observations with the same two balanced cell types. The biological embedding separates those types. In the technical embedding, each compact group contains equal numbers of both types. Actual KMeans provides the predicted cluster labels.

| Candidate, seed 0 | Released call: cluster labels | Cell-type labels | ARI, clusters versus cell types |
|---|---:|---:|---:|
| Biological separation | 0.9192562199 | 0.9192562199 | 1.0000000000 |
| Technical separation; mixed cell types | **0.9963883078** | **0.4918026995** | -0.0084745763 |

The current call prefers the technical embedding. The cell-type call prefers the biological embedding. This reverses **one metric's comparison**, not a reconstructed multi-metric publication ranking.

These scores use scib's normalization `(raw silhouette + 1) / 2`; 0.492 is close to raw silhouette zero, not 49.2% classification accuracy. The designed construction does not estimate the frequency or magnitude of this effect in real benchmarks.

## Reproduction and limits

The full local audit extracted and executed the original ASW assignment from the complete, hash-verified benchmark source using Python's AST. The corrected call changed only `label_key`. The numerical silhouette body was taken from scib v1.1.5 and called real scikit-learn. A SimpleNamespace supplied pandas/NumPy storage instead of AnnData. The scib helper was a marked excerpt, not a separately hash-verified complete module. That scib version is an audit reference, not an established publication dependency.

The full local suite passed all 30 designed seed pairs, 120 independent direct-formula comparisons, 120 row-permutation comparisons, 120 label-renaming comparisons and 120 common transformation/scale comparisons. Changing biological labels alone left the released value unchanged.

The **compact public script** hosted here was separately executed. It uses the same fixture, calls sklearn directly, records all 30 seeds and checks 120 values against a direct mathematical implementation. It is not represented as the full AST-based harness or a native scib pipeline.

```sh
python research/scmultibench-silhouette/minimal_reproducer.py
```

Local environment: Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, pandas 2.2.3, scikit-learn 1.8.0, threadpoolctl 3.6.0. See the shared dependency file and the environment emitted by the script.

Not executed locally: full scMultiBench CLI, native AnnData/scanpy/scib integration, original publication embeddings or aggregate rankings. The numerical table tests ordinary ASW. The proposed iASW line has the same label-source mismatch but has not undergone a separate numerical iASW reanalysis.

## Related isolation-policy question

Batches are numbered from 1, while `num = np.max(batch)+1` is supplied as `iso_threshold`. With B batches, that admits labels present in up to B+1 batches: every observed label. The extracted scib `get_isolated_labels` body confirmed this on a three-batch example. Its default selected only the one-batch label; threshold 4 also selected both ubiquitous labels. The intended policy needs author clarification. The patch does not silently replace it.

## Submission

Issue #4 was submitted publicly on 7 September 2026. The source, tests, results and proposed patch were also sent to corresponding author Pengyi Yang in the existing correspondence thread. No author acknowledgement, accepted correction or revised recommendation is claimed. Original embeddings and labels are needed to measure publication effects.

[scib silhouette reference](https://github.com/theislab/scib/blob/v1.1.5/scib/metrics/silhouette.py) · [isolated-label reference](https://github.com/theislab/scib/blob/v1.1.5/scib/metrics/isolated_labels.py) · [all audit reports](../)
