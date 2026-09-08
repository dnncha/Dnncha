# Scientific code audits

Donncha O'Toole · Cheerful Duck · 8 September 2026

Reports, executable counterexamples and proposed fixes for computational research. These are technical reports, not peer-reviewed corrections. A demonstrated error in released code does not by itself establish which published conclusions change.

## Reports

| Investigation | Established result | Publication impact not yet established |
|---|---|---|
| [scMultiBench: category metadata reverses spatial matching scores](scmultibench-paa-categories/) | Reordering one slice's category metadata changes correct/wrong test-coupling scores from 1/0 to 0/1. Source-verified scoring checks passed in five released copies; the first three also have native AnnData persistence checks. | Original category metadata and couplings have not been reanalysed. |
| [scMultiBench: ASW uses inferred clusters instead of biological cell types](scmultibench-scib-native/) | Native scib reproduces the label-source reversal. On the 28,574-cell released embedding demo, released cluster ASW is 0.614295 vs cell-type ASW 0.569601. | Demo is not identified as a named original-paper run; method rankings have not been recomputed. |
| [scMultiBench: isolated-label threshold admits every label](scmultibench-scib-native/) | With three batches the released threshold is 4. Native scib shows a synthetic iASW preference reversal; the released demo selects all 28 cell types instead of the one one-batch type under scib's default policy. | Exact publication environment and intended isolation rule need author confirmation before calling a corrected paper result. |
| [SABench: common rotation reverses a scoring comparison](sabench-rotation/) | Rotating the reference and both constructed candidates together changes the selected observations and reverses their scores. Native AnnData verification passed for both pinned source files. | Original method rankings have not been rerun. |
| [scMultiBench: failed classes disappear from macro F1](scmultibench-native-r/) | Zero-TP classes are dropped instead of scoring zero. Native R confirms a constructed five-metric ranking reversal after correcting F1 alone. | Synthetic comparison, not a corrected publication leaderboard. The released demo has no zero-TP classes and its F1 is unchanged. |
| [scMultiBench: precision reported as specificity](scmultibench-native-r/) | The released specificity expression is precision. Native R changes the released 16,305-cell demo value from 0.870108 to 0.994996. | The demo is not established as a named original-paper run. D51/D52 term-removal results remain sensitivity analyses, not corrected specificity rankings. |
| [scPerturBench: reversed baseline training direction](scperturbench-release-reachability/) | Two baseline families are trained in the opposite direction to their prediction task. A pinned-source inventory locates 1,736 baseline rows across 12 released datasets; these are not recomputed predictions. | Original publication rankings and conclusions have not been recomputed. |

The five scMultiBench entries concern different defects in **one paper**, not five publications. No misconduct, first-discovery guarantee or accepted correction is alleged. Upstream discussions: [specificity #2](https://github.com/PYangLab/scMultiBench/issues/2), [F1 #3](https://github.com/PYangLab/scMultiBench/issues/3), [ASW label source #4](https://github.com/PYangLab/scMultiBench/issues/4), [PAA category codes #5](https://github.com/PYangLab/scMultiBench/issues/5), [isolated-label threshold #6](https://github.com/PYangLab/scMultiBench/issues/6).

## Reproduce

Use isolated environments. Dependencies record audit/reference versions, not reconstructed publication environments. Individual reports define their execution scope.

```sh
python -m pip install -r research/requirements.txt
python research/scmultibench-silhouette/minimal_reproducer.py
python research/sabench-rotation/minimal_reproducer.py --source research/sabench-rotation/upstream_excerpt.py
```

Native R evaluator:

```sh
python research/scmultibench-native-r/fetch_sources.py
Rscript research/scmultibench-native-r/reproduce.R
```

Native PAA check:

```sh
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.14.1 anndata==0.10.9 'zarr<3'
python research/scmultibench-paa-categories/verify_native.py
python research/scmultibench-paa-categories/verify_additional_paths.py
```

Native scib and released embedding demo:

```sh
python -m pip install 'numpy==1.26.4' 'pandas==2.2.3' 'scipy==1.14.1' 'scikit-learn==1.5.2' 'h5py==3.16.0' 'anndata==0.10.9' 'scanpy==1.10.4' 'scib==1.1.5'
python research/scmultibench-scib-native/verify_native.py
python research/scmultibench-scib-native/reanalyse_released_demo.py
```

## Corrections and review

Open an issue here with counter-evidence, a reproduction problem or a source correction. Reports are prepared with AI assistance and reviewed against executable checks; that is not independent scientific peer review.

The earlier hard-coded-alpha/coordinate-units suspicion in SABench was dropped after checking the library's default normalization. It is not a finding. The F1 part of the initial suggested specificity fix retained the zero-class error; issue #3 and the follow-up in issue #2 correct that suggestion.

The [Cheerful Duck Research library](https://cheerfulduck.com/research) is live. Its [benchmark reports](https://cheerfulduck.com/research/audits), [study-impact discussion](https://cheerfulduck.com/research/study-impact) and [correction record](https://cheerfulduck.com/research/corrections) link to this evidence. The routes were checked again on 8 September 2026; the earlier 7 September 404 observation no longer describes the current site.
