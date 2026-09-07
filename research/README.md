# Scientific code audits

Donncha O'Toole · Cheerful Duck · 7 September 2026

Reports, executable counterexamples and proposed fixes for computational research. These are technical reports, not peer-reviewed corrections. A demonstrated error in released code does not by itself establish which published conclusions change.

## Reports

| Investigation | Established result | Publication impact not yet established |
|---|---|---|
| [scMultiBench: category metadata reverses spatial matching scores](scmultibench-paa-categories/) | Reordering one slice's category metadata changes correct/wrong test-coupling scores from 1/0 to 0/1. Native AnnData checks passed in three released copies. | Original category metadata and couplings have not been reanalysed. |
| [SABench: common rotation reverses a scoring comparison](sabench-rotation/) | Rotating the reference and both constructed candidates together changes the selected observations and reverses their scores. Native AnnData verification passed for both pinned source files. | Original method rankings have not been rerun. |
| [scMultiBench: cell-type silhouette uses predicted clusters](scmultibench-silhouette/) | The released ASW call favours a constructed embedding with compact technical groups but mixed biological labels. Changing the label source reverses that metric's preference. | Original embeddings and aggregate rankings have not been rerun. |
| [scMultiBench: failed classes disappear from macro F1](scmultibench-native-r/) | Zero-TP classes are dropped instead of scoring zero. Native R confirms a constructed five-metric ranking reversal after correcting F1 alone. | Synthetic comparison, not a corrected publication leaderboard. The released demo has no zero-TP classes and its F1 is unchanged. |
| [scMultiBench: precision reported as specificity](scmultibench-native-r/) | The released specificity expression is precision. Native R changes the released 16,305-cell demo value from 0.870108 to 0.994996. | The demo is not established as a named original-paper run. D51/D52 term-removal results remain sensitivity analyses, not corrected specificity rankings. |
| [scPerturBench: reversed baseline training direction](https://github.com/bm2-lab/scPerturBench/issues/13) | Two baseline families are trained in the opposite direction to their prediction task in the released cellular-context code. | Original publication rankings and conclusions have not been recomputed. |

The four scMultiBench entries concern different defects in **one paper**, not four publications. No misconduct, first-discovery guarantee or accepted correction is alleged. Existing upstream discussions: [specificity #2](https://github.com/PYangLab/scMultiBench/issues/2), [F1 #3](https://github.com/PYangLab/scMultiBench/issues/3), [silhouette #4](https://github.com/PYangLab/scMultiBench/issues/4).

## Reproduce

Use isolated environments. Dependencies record the audit versions, not the papers' original environments. Individual reports provide the native checks and full execution scope.

```sh
python -m pip install -r research/requirements.txt
python research/scmultibench-silhouette/minimal_reproducer.py
python research/sabench-rotation/minimal_reproducer.py --source research/sabench-rotation/upstream_excerpt.py
```

For the native R evaluator, use Python 3 and R 4.4.3:

```sh
python research/scmultibench-native-r/fetch_sources.py
Rscript research/scmultibench-native-r/reproduce.R
```

For the native PAA check, use Python 3.11 in a separate environment:

```sh
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.14.1 anndata==0.10.9 'zarr<3'
python research/scmultibench-paa-categories/verify_native.py
```

The compact Python scripts are numerical counterexamples. Their reports distinguish these runs from more extensive tests and native pipeline execution. No original publication datasets are bundled.

## Corrections and review

Open an issue here with counter-evidence, a reproduction problem or a source correction. Reports are prepared with AI assistance and reviewed against executable checks; that is not independent scientific peer review.

The earlier hard-coded-alpha/coordinate-units suspicion in SABench was dropped after checking the library's default normalization. It is not a finding. The F1 part of the initial suggested specificity fix retained the zero-class error; issue #3 and the follow-up in issue #2 correct that suggestion.

These files are public on GitHub. The proposed Cheerful Duck website routes returned 404 when checked on 7 September 2026; a private-repository merge was not a verified website publication.
