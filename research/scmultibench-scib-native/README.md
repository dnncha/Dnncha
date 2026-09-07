# scMultiBench: native scib verification and released embedding reanalysis

Donncha O'Toole · Cheerful Duck · 7 September 2026

Two independent defects in the released embedding evaluator are now reproduced with **real scib and AnnData**, and measured on the complete embedding demo committed to the scMultiBench repository.

1. `ASW_cellType` is calculated from inferred `cluster` labels rather than the supplied biological `celltype` labels ([upstream issue #4](https://github.com/PYangLab/scMultiBench/issues/4)).
2. The isolated-label metrics receive `iso_threshold = max(batch) + 1`; with B batches this is B+1, so every observed label satisfies the threshold ([upstream issue #6](https://github.com/PYangLab/scMultiBench/issues/6)).

[Successful public run](https://github.com/dnncha/Dnncha/actions/runs/34139782478) · [native scib test](verify_native.py) · [released-demo reanalysis](reanalyse_released_demo.py)

These are evaluator measurements and counterexamples. The released demo has not been identified as a named original-publication run, so the numbers below are **not a corrected paper leaderboard**.

## What the released code does

At scMultiBench commit `0c68f87d554a52e363dbfda2a9d1fa9538eeae9f`, the complete 5,723-byte evaluator contains:

```python
batch = read_batch(args.cty_path)
num = np.max(batch)+1
...
asw = scib.me.silhouette(adata_integrated, label_key="cluster", embed="X_emb")
print("ASW_cellType:", asw)
iasw = scib.me.isolated_labels_asw(
    adata_integrated,
    batch_key="batch",
    label_key="cluster",
    embed="X_emb",
    iso_threshold=num,
)
if1 = scib.me.isolated_labels_f1(
    adata_integrated,
    batch_key="batch",
    label_key="celltype",
    cluster_key="cluster",
    embed="X_emb",
    iso_threshold=num,
)
```

The evaluator's Git blob is `b8549d293d2a6eaef9af91bd7842dc68e15e9fcf`.

scMultiBench's evaluation environment installs `scib` without pinning its version. For the native audit I therefore used scib **1.1.5 as an explicit reference implementation**, not as a claim that it was the exact version used for the publication. The complete v1.1.5 `isolated_labels.py` and `silhouette.py` sources were Git-blob verified, and the imported function ASTs match those pinned sources.

In scib 1.1.5, `iso_threshold` is the maximum number of batches in which a label may occur and still be treated as isolated. With `None`, scib uses the minimum observed batch count among labels. Passing B+1 therefore admits every label.

## Native synthetic verification

The native test runs Python 3.10.21, scib 1.1.5, AnnData 0.10.9, NumPy 1.26.4, pandas 2.2.3 and scikit-learn 1.5.2.

### Label-source reversal

The same 120 observations and biological labels are embedded in two ways. One embedding separates the cell types. The other contains extremely compact technical groups that mix the two cell types. KMeans supplies the inferred clusters.

| Candidate | Released ASW using `cluster` | ASW using `celltype` |
|---|---:|---:|
| Biological separation | 0.9192562199 | 0.9192562199 |
| Compact technical groups, mixed cell types | **0.9963883078** | **0.4918026995** |

The released call prefers the biologically mixed embedding; the cell-type call prefers the biologically separated embedding.

### Isolation-threshold reversal

The second fixture has three batches. `C1`–`C4` occur in all three; `R` occurs only in batch 1. scib's default isolation policy selects only `R`. The released rule calculates `num = 4` and selects all five labels.

| Candidate | scib default isolated-label iASW | Released threshold `4` iASW |
|---|---:|---:|
| A: isolated label R well preserved; common labels overlap | **0.9354775053** | 0.5656422721 |
| B: common labels well separated; R overlaps a common label | 0.5251509457 | **0.7723953788** |

The metric preference reverses. This fixture was designed to expose the policy difference; it does not estimate how often such reversals occur in real benchmark data.

## Reanalysis of the released embedding demo

The repository contains the exact files used in the evaluator's example command: three biological-label CSVs, a 15-dimensional embedding, and a clustering result. All five complete files were downloaded at the pinned scMultiBench commit and verified by Git blob before calculation.

The demo contains **28,574 observations, three batches, 28 biological cell types and 28 inferred clusters**.

### Ordinary ASW

| Calculation on the same released embedding | Score |
|---|---:|
| Released call: silhouette of inferred clusters | **0.6142954826** |
| Cell-type silhouette | **0.5696005523** |

Changing only the label source changes the reported quantity by about **0.044695** on this released demo. This is not a model improvement or degradation; these are two different label partitions evaluated on the same coordinates.

### Isolated-label selection

With three batches, scMultiBench passes `num = 4`. That threshold admits **all 28 biological cell types**.

Under scib 1.1.5's default isolation rule, the minimum batch presence is one. Only **`Erythroid `** occurs in one batch, so it is the single isolated biological label. Two other types occur in two batches; the remaining 25 occur in all three.

### iASW decomposition

The released iASW call has both defects at once: it uses cluster labels and threshold 4. To separate them, the same silhouette samples were aggregated three ways:

| Calculation | iASW |
|---|---:|
| Released: cluster labels + threshold 4 | **0.6303640834** |
| Fix label source only: cell types + threshold 4 | **0.5768824066** |
| Cell types + scib default isolated-label policy | **0.8656384051** |

The final value is the scaled silhouette of the one isolated cell type, `Erythroid `, under this reference policy. It should not be read as a corrected publication result until the authors confirm that scib's default isolation definition was their intended benchmark definition.

An important nuance: every inferred cluster in this released demo occurs in all three batches. If isolation is incorrectly defined over `cluster`, scib's default minimum-batch rule would also select every cluster. That is another reason the label-source and threshold questions must be resolved together rather than patching one number mechanically.

## Source and execution integrity

Pinned source blobs:

- scMultiBench `scib_metrics.py`: `b8549d293d2a6eaef9af91bd7842dc68e15e9fcf`
- scib v1.1.5 `isolated_labels.py`: `2e8258ab79f972cd983f902f20e3cb247db820cc`
- scib v1.1.5 `silhouette.py`: `8d44b3aa8c2e90e3e1792db35efc7ca4fdc25a7a`

Released-demo input blobs:

- `cty1.csv`: `bc04ec13316d61b673827fe6cc028787284bd341`
- `cty2.csv`: `a156ed8c1165b6abe57985487f2d3d70bb389b56`
- `cty3.csv`: `1b69f1c6c1be922dde3c41fa13641657c4f8175a`
- `embedding.h5`: `203bbdbacaa345fb898ce26fa7b53322c12fe471`
- `sinfonia_clustering.h5`: `445b9c4d41e24a46344b37611e79a52a29911d84`

Run `34139782478` passed. Its ten-file evidence archive contains both complete source snapshots, both complete numerical result records, per-observation silhouette samples, logs and the dependency environment. The archive was downloaded and independently checksum-verified as SHA-256 `4d038bee0a0795596c2f3d6af61de588944dcdc2db137035fdfcb33546d7035c`.

The released-demo arithmetic uses `sklearn.metrics.silhouette_samples` once for clusters and once for cell types, then applies the exact scib v1.1.5 aggregation/scaling formulas whose native functions were independently source-verified in the companion test. This avoids recalculating the 28,574-by-28,574 distance problem for each iASW variant while preserving the metric arithmetic.

## What remains

The strongest remaining scientific step is to identify the exact embeddings/labels used for the publication's reported method comparisons and rerun all affected methods under a confirmed metric definition. The repository demo is real released data, but it is not enough to claim that a named published method rank changes.

The iF1 graph/embedding paths also receive the B+1 threshold. The label-selection defect is established; a publication-level iF1 reanalysis still requires the relevant original graph/cluster outputs and a confirmed isolation rule.

No misconduct, accepted correction or journal action is alleged. Counter-evidence and author clarification should update this report.

[Issue #4: ASW label source](https://github.com/PYangLab/scMultiBench/issues/4) · [Issue #6: isolated-label threshold](https://github.com/PYangLab/scMultiBench/issues/6) · [All scientific audit reports](../)
