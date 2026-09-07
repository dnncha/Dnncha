# Rotating both slices changes SABench's landmark score

Donncha O'Toole · 7 September 2026 · Cheerful Duck

SABench's released `Overlap_accuracy` function can reverse two candidate alignments' scores when the entire comparison is rotated. Every cross-slice distance is preserved; the relative alignment is unchanged.

| Common rotation | Candidate A | Candidate B | Higher score |
|---|---:|---:|---|
| 0 degrees | 6/8 = 0.75 | 2/8 = 0.25 | A |
| 45 degrees | 2/6 = 0.333333 | 5/8 = 0.625 | B |

**This is an executed synthetic counterexample, not corrected scores for the paper's original methods.** The 12-point fixture is in the reproducer. Candidate A shifts the points by `[1.3,0.4]`; B by `[-0.4,1.1]`. Labels travel with the points. The reference and both candidates then receive the same rotation.

## Why it happens

The function finds overlap by intersecting the slices' axis-aligned bounding boxes. Rotating the tissues together changes those rectangles. Different reference and query observations enter the nearest-neighbour calculation, changing both its possible matches and denominator.

Holding the original observation-selection masks fixed preserves the scores. Removing the crop entirely also gives invariant scores. Those are diagnostic controls, not validated biological definitions of tissue overlap.

Source pin: `Yunzhi-Yan/SABench` commit `54d4e17c6dff5eab7ad93fee2a9bd70385ac750b`.

- [Tutorial function, lines 336–386](https://github.com/Yunzhi-Yan/SABench/blob/54d4e17c6dff5eab7ad93fee2a9bd70385ac750b/Tutorial/SABench.py#L336-L386)
- [Landmark evaluation notebook](https://github.com/Yunzhi-Yan/SABench/blob/54d4e17c6dff5eab7ad93fee2a9bd70385ac750b/FeatureSimilarity/LandmarkBased.ipynb)
- [Associated Nature Computational Science paper](https://www.nature.com/articles/s43588-026-00977-z)

## Execution

The original numerical function excerpt was executed with real NumPy, SciPy and pandas. An explicit adapter supplied data storage and boolean row selection instead of AnnData. The compact script hosted here was rerun successfully before publication. It verifies all cross-slice distances and the four scores.

The earlier extended local run additionally checked an independent brute-force calculation, nearest-neighbour tie margins, fixed-support controls, 30 coordinate-jitter seeds and common rotations from 40 through 50 degrees. The reversal survived those tests. These checks concern the constructed fixture, not its frequency in real data.

Local environment: Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, pandas 2.2.3. The bundled file is a marked function excerpt, not the complete upstream blob. The compact reproducer verifies the full Git blob when passed a complete file named `SABench.py`; that complete-blob native run was not completed at this report's publication. The `--native` option is supplied for actual AnnData, not claimed as a completed local run. Earlier private CI failed before executing any steps.

```sh
python research/sabench-rotation/minimal_reproducer.py --source research/sabench-rotation/upstream_excerpt.py
```

From a complete pinned upstream checkout with AnnData installed:

```sh
python /path/to/minimal_reproducer.py --source Tutorial/SABench.py --native
```

The excerpt's SHA-256 is `e8b54ea2549c0a8c801f4947a8b858b0e5b2ace62848f764f7f93ff4b4763386`.

## Author contact and limits

The report and evidence packet were sent to corresponding author Bin-Zhi Qian on 7 September 2026. No delivery/read acknowledgement or accepted correction is claimed. The upstream issue creation was refused with HTTP 403, so no SABench upstream issue was created. This public report is an independent record of the counterexample.

The authors were asked whether an intended canonical-orientation step was missed. Original aligned coordinates and region labels would allow the test to be applied to the publication's actual outputs; expression matrices and retraining are unnecessary for that test. A replacement overlap definition needs agreement about the intended quantity, rather than silently substituting a new metric.

The earlier suspicion that hard-coded alpha alone causes uniform coordinate-units dependence was dropped: the alpha-shape library normalizes its input by default. It is not reported as a defect.

[All scientific audit reports](../)
