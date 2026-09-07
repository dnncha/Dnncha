# Scientific code audits

Donncha O'Toole · Cheerful Duck · 7 September 2026

Reports, executable counterexamples and proposed fixes for computational research. These are technical reports, not peer-reviewed corrections. A demonstrated error in released code does not by itself establish which published conclusions change.

## Reports

| Investigation | Established result | Publication impact not yet established |
|---|---|---|
| [SABench: common rotation reverses a scoring comparison](sabench-rotation/) | Rotating the reference and both constructed candidates together changes the selected observations and reverses their scores. | Original method rankings have not been rerun. |
| [scMultiBench: cell-type silhouette uses predicted clusters](scmultibench-silhouette/) | The released ASW call favours a constructed embedding with compact technical groups but mixed biological labels. Changing the label source reverses that metric's preference. | Original embeddings and aggregate rankings have not been rerun. |
| [scMultiBench: failed classes disappear from macro F1](https://github.com/PYangLab/scMultiBench/issues/3) | Zero-TP classes are dropped instead of scoring zero. A count-formula correction reverses a constructed five-metric comparison. | Synthetic comparison, not a corrected publication leaderboard; native R pending. |
| [scMultiBench: precision reported as specificity](https://github.com/PYangLab/scMultiBench/issues/2) | The released specificity expression is precision. | D51/D52 term-removal results are sensitivity analyses, not corrected specificity rankings. |
| [scPerturBench: reversed baseline training direction](https://github.com/bm2-lab/scPerturBench/issues/13) | Two baseline families are trained in the opposite direction to their prediction task in the released cellular-context code. | Original publication rankings and conclusions have not been recomputed. |

The three scMultiBench entries concern different defects in **one paper**, not three publications. No misconduct, first-discovery guarantee or accepted correction is alleged.

## Reproduce the two reports hosted here

Use an isolated Python environment. The dependency file records the local versions, not the papers' original environments.

```sh
python -m pip install -r research/requirements.txt
python research/scmultibench-silhouette/minimal_reproducer.py
python research/sabench-rotation/minimal_reproducer.py --source research/sabench-rotation/upstream_excerpt.py
```

The compact scripts are self-contained numerical counterexamples. Their reports distinguish these runs from the more extensive local tests and from full native pipeline execution. No original publication datasets are bundled.

## Corrections and review

Open an issue here with counter-evidence, a reproduction problem or a source correction. Upstream discussions are linked above. Reports are prepared with AI assistance and reviewed against executable checks; that is not independent scientific peer review.

The earlier hard-coded-alpha/coordinate-units suspicion in SABench was dropped after checking the library's default normalization. It is not a finding. The F1 part of the initial suggested specificity fix retained the zero-class error; issue #3 and the follow-up in issue #2 correct that suggestion.

These files are public on GitHub. The proposed Cheerful Duck website routes returned 404 when checked on 7 September 2026; a private-repository merge was not a verified website publication.
