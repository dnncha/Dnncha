# scMultiBench: native R verification and the released prediction demo

Donncha O'Toole · Cheerful Duck · 7 September 2026

The original R evaluator has now been executed in R 4.4.3. The specificity error and the failed-class F1 error reproduce natively. No Python translation or data-container adapter is used for this run.

[Successful public execution](https://github.com/dnncha/Dnncha/actions/runs/34128607057) · [R reproducer](reproduce.R) · [source verification](fetch_sources.py)

## Released demo: 16,305 observations, 26 classes

The original function was run directly on the repository's `data/classification/demo_result/query.csv` and `predict.csv`. All three complete input blobs, including the evaluator, were verified against commit `0c68f87d554a52e363dbfda2a9d1fa9538eeae9f`.

| Metric | Original evaluator | F1 and specificity corrected |
|---|---:|---:|
| Overall accuracy | 0.879668813247470 | 0.879668813247470 |
| Average accuracy | 0.777752840511994 | 0.777752840511994 |
| Specificity | **0.870107570032222** | **0.994995899305141** |
| Sensitivity | 0.777752840511994 | 0.777752840511994 |
| Macro F1 | 0.804534481651323 | 0.804534481651323 |

The specificity change is about 0.1249, or 12.49 percentage points. This is not an improvement in a model: the same predictions are being evaluated using the correct denominator instead of precision.

There are **no zero-true-positive classes in this demo**. Consequently its F1 is unchanged by the F1 correction. The demo is a negative control for that error, not evidence that all results are affected.

These files are released examples. They have not been identified as the exact outputs of a named original-publication run, and there is only one prediction vector here. This is not a corrected paper leaderboard.

## Native regression results

Six explicit confusion-matrix fixtures and 200 seeded random matrices were tested. The corrected calculations agree with an independent oracle that counts one-vs-rest decisions from the individual labels. Correcting F1 alone leaves the other four outputs unchanged.

The earlier constructed five-metric comparison also reproduces in native R:

| Calculation | Candidate A mean rank | Candidate B mean rank |
|---|---:|---:|
| Original | 1.6 | 1.4 |
| F1 correction alone | 1.4 | 1.6 |
| F1 and specificity corrections | 1.4 | 1.6 |

Larger mean rank is better in the released ranking rule. These are the selected synthetic matrices documented in [upstream issue #3](https://github.com/PYangLab/scMultiBench/issues/3), not published method results. The specificity report is [issue #2](https://github.com/PYangLab/scMultiBench/issues/2).

## Reproduce

Run with Python 3 and R 4.4.3; only base R is required.

```sh
python research/scmultibench-native-r/fetch_sources.py
Rscript research/scmultibench-native-r/reproduce.R
```

The script evaluates the original first R code block, then creates two in-memory variants changing only the F1 formula or that formula plus specificity. The original source remains unchanged on disk. Outputs include all test metrics, the demo confusion matrix, per-class counts, rank comparisons and `sessionInfo()`.

The executed research-code commit is `4551ce1fd06018d56c043c305746e5ac278e52a4`; the PR job checked out merge commit `399786c516daadd8debf40f82fe8a84346f9ccb6`. Run `34128607057` passed on 7 September 2026. The seven-file evidence ZIP was downloaded and its SHA-256 independently checked as `8826d76ffbf6217e2575f05cefee39f537ab689921724546a13cbd9c6541dd7c`.

The evidence artifact contains the complete generated metrics, per-class counts, confusion matrix, input manifest, session information and execution log. These audit dependencies are not a reconstruction of the paper's original environment.

[All scientific audit reports](../)
