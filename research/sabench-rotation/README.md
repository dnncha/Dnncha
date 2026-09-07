# Rotating both slices changes SABench's landmark score

Donncha O'Toole · 7 September 2026 · Cheerful Duck

**Update, 7 September: the native AnnData check has now passed for both complete, hash-verified upstream source files.** [Public execution](https://github.com/dnncha/Dnncha/actions/runs/34127473227) · [machine-readable result](native-result.json) · [native reproducer](verify_native.py).

SABench's released `Overlap_accuracy` function reverses two constructed candidate alignments' scores when the entire comparison is rotated. Every cross-slice distance is preserved; the relative alignment is unchanged.

| Common rotation | Candidate A | Candidate B | Higher score |
|---|---:|---:|---|
| 0 degrees | 6/8 = 0.75 | 2/8 = 0.25 | A |
| 45 degrees | 2/6 = 0.333333 | 5/8 = 0.625 | B |

**This is an executed synthetic counterexample, not corrected scores for the paper's original methods.** The 12-point fixture is in the reproducers. Candidate A shifts the points by `[1.3,0.4]`; B by `[-0.4,1.1]`. Labels travel with the points. The reference and both candidates then receive the same rotation.

## Why it happens

The function finds overlap by intersecting the slices' axis-aligned bounding boxes. Rotating the tissues together changes those rectangles. Different reference and query observations enter the nearest-neighbour calculation, changing both possible matches and denominator.

Holding the original observation-selection masks fixed preserves the scores. Removing the crop entirely also gives invariant scores. Those are diagnostic controls, not validated biological definitions of overlap.

Source pin: `Yunzhi-Yan/SABench` commit `54d4e17c6dff5eab7ad93fee2a9bd70385ac750b`.

- [Tutorial function, lines 336–386](https://github.com/Yunzhi-Yan/SABench/blob/54d4e17c6dff5eab7ad93fee2a9bd70385ac750b/Tutorial/SABench.py#L336-L386)
- [Landmark evaluation notebook](https://github.com/Yunzhi-Yan/SABench/blob/54d4e17c6dff5eab7ad93fee2a9bd70385ac750b/FeatureSimilarity/LandmarkBased.ipynb)
- [Associated Nature Computational Science paper](https://www.nature.com/articles/s43588-026-00977-z)

## Native execution

Public run `34127473227`, tested commit `028bfe6f5ef738a85637ca257b6aa5a8b0a4058f`, downloaded the complete 26,771-byte Python source and 159,298-byte notebook from that immutable pin. Their Git blob SHAs matched `72990d43138389d359caa1a0b378d5deff969bfd` and `a56f85286ae48d27799d78624e3b0a4e59f625f3`, respectively. The overlap function ASTs match.

Only the original `Overlap_accuracy` and `Average_Accuracy` definitions were executed, with **actual AnnData, NumPy, pandas and SciPy**. Both source locations reproduce all four scores. Cross-slice distances are invariant within the stated tolerances; the averaging wrapper agrees; input coordinates are unchanged. Notebook top-level jobs, other metrics and original publication datasets were not executed.

Environment: Python 3.11.16, NumPy 1.26.4, SciPy 1.14.1, pandas 2.2.3, AnnData 0.10.9, h5py 3.16.0, zarr 2.18.7. These are audit dependencies, not a reconstruction of the paper's entire software environment.

The downloaded CI archive and both complete source blobs were independently checksum-checked in the local audit environment. Archive SHA-256: `e72aa7c7129b6d93444f751b8a6da42c475cb17ac131600c06bfebaef390d425`. The CI artifact contains source snapshots, logs, package versions and results; the result JSON is also committed here so it does not depend on artifact retention.

```sh
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.14.1 anndata==0.10.9 'zarr<3'
python research/sabench-rotation/verify_native.py
```

## Earlier local checks

The first local run used an explicit data-container adapter with real numerical libraries. It also checked an independent brute-force calculation, nearest-neighbour tie margins, fixed-support controls, 30 coordinate-jitter seeds and common rotations from 40 through 50 degrees. The reversal survived those checks. They concern the constructed fixture, not its frequency in real data. That extended test set was not silently relabelled as the later native run.

The compact adapter-based reproducer remains available:

```sh
python research/sabench-rotation/minimal_reproducer.py --source research/sabench-rotation/upstream_excerpt.py
```

Its marked source excerpt has SHA-256 `e8b54ea2549c0a8c801f4947a8b858b0e5b2ace62848f764f7f93ff4b4763386`. Earlier private CI failed before executing any steps; the later public native run above supersedes the previous native-execution gap.

## Author contact and limits

The initial report and evidence packet were sent to corresponding author Bin-Zhi Qian on 7 September 2026. No delivery/read acknowledgement or accepted correction is claimed. The upstream issue creation was refused with HTTP 403, so no SABench upstream issue was created. This public report records the counterexample independently.

The authors were asked whether an intended canonical-orientation step was missed. Original aligned coordinates and region labels would allow the test to be applied to the publication's actual outputs; expression matrices and retraining are unnecessary for that test. A replacement overlap definition needs agreement about the intended quantity, rather than silently substituting a new metric.

The earlier suspicion that hard-coded alpha alone causes uniform coordinate-units dependence was dropped: the alpha-shape library normalizes its input by default. It is not reported as a defect.

[All scientific audit reports](../)
