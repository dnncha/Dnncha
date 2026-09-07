"""Measure reachability of the reported baseReg/baseMLP defect in released result tables.

This DOES NOT compute corrected predictions. It verifies immutable public result CSVs
from scPerturBench-reproducibility and inventories the affected baseline rows they
contain, so implementation reachability is separated from corrected-effect claims.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

COMMIT = "e9800bd01039afacdfc7197dbe406731d2f998f0"
BASE = f"https://raw.githubusercontent.com/bm2-lab/scPerturBench-reproducibility/{COMMIT}/"
FILES = {
    "iid_top100": ("Results/Cellular_context_iid/cellular_iid_performance_top100.csv", "54cbc93b3ee2dbcd7469a64b961b017d76f0e5f6"),
    "iid_top5000": ("Results/Cellular_context_iid/cellular_iid_performance_top5000.csv", "0ed3dfa196b06c5faa906f73c776cd1c5ad46ebe"),
    "ood_top100": ("Results/Cellular_context_ood/cellular_ood_performance_top100.csv", "2afcc0ec620b139001303a32878f976f2a0eca24"),
    "ood_top5000": ("Results/Cellular_context_ood/cellular_ood_performance_top5000.csv", "4e0ee77d1c9de758ad83f368a0269db13decd4d5"),
}
TARGETS = {"baseReg", "baseMLP"}
OUT = Path(__file__).resolve().parent / "result.json"


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def fetch(path: str, expected: str) -> tuple[bytes, str]:
    url = BASE + path
    with urlopen(Request(url, headers={"User-Agent": "CheerfulDuck-scientific-code-audit"}), timeout=45) as r:
        raw = r.read(20_000_001)
    if len(raw) > 20_000_000:
        raise RuntimeError(f"Unexpectedly large result file: {path}")
    actual = git_blob_sha(raw)
    if actual != expected:
        raise RuntimeError(f"Git blob mismatch for {path}: {actual} != {expected}")
    return raw, url


def as_float(value: str):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def summarize_numeric(values):
    vals = [v for v in (as_float(x) for x in values) if v is not None]
    if not vals:
        return None
    return {
        "n": len(vals), "min": min(vals), "median": statistics.median(vals),
        "mean": statistics.fmean(vals), "max": max(vals),
    }


def analyze(name: str, path: str, expected: str):
    raw, url = fetch(path, expected)
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    fields = reader.fieldnames or []
    if not rows or not fields:
        raise RuntimeError(f"No rows/headers: {path}")

    # Identify the method field from actual values rather than assuming a header.
    scores = {f: sum((r.get(f) or "") in TARGETS for r in rows) for f in fields}
    method_col, hits = max(scores.items(), key=lambda x: x[1])
    if hits == 0:
        raise RuntimeError(f"Could not find baseReg/baseMLP values in {path}")

    method_counts = Counter((r.get(method_col) or "") for r in rows)
    target_rows = [r for r in rows if (r.get(method_col) or "") in TARGETS]

    # Preserve column-level structure for later independent review without dumping rows.
    column_profiles = {}
    for f in fields:
        vals = [(r.get(f) or "") for r in target_rows]
        numeric = summarize_numeric(vals)
        uniq = sorted(set(vals))
        column_profiles[f] = {
            "unique_count": len(uniq),
            "examples": uniq[:12],
            "numeric": numeric,
        }

    likely_dataset_cols = [f for f in fields if "dataset" in f.lower() or "data_set" in f.lower()]
    likely_rank_cols = [f for f in fields if "rank" in f.lower()]
    likely_case_cols = [f for f in fields if any(k in f.lower() for k in ("sample", "perturb", "cell", "condition", "case"))]

    by_method = {}
    for method in sorted(TARGETS):
        mr = [r for r in rows if (r.get(method_col) or "") == method]
        by_method[method] = {
            "rows": len(mr),
            "datasets": {f: sorted(set((r.get(f) or "") for r in mr)) for f in likely_dataset_cols},
            "rank_columns": {f: summarize_numeric([(r.get(f) or "") for r in mr]) for f in likely_rank_cols},
            "case_columns": {f: {"unique_count": len(set((r.get(f) or "") for r in mr)), "examples": sorted(set((r.get(f) or "") for r in mr))[:10]} for f in likely_case_cols},
        }

    return {
        "name": name,
        "path": path,
        "url": url,
        "bytes": len(raw),
        "git_blob_sha1": git_blob_sha(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rows_total": len(rows),
        "columns": fields,
        "method_column": method_col,
        "method_counts": dict(method_counts),
        "affected_baseline_rows": len(target_rows),
        "by_method": by_method,
        "column_profiles_for_affected_rows": column_profiles,
    }


def main():
    summaries = [analyze(name, path, sha) for name, (path, sha) in FILES.items()]
    total_target = sum(s["affected_baseline_rows"] for s in summaries)
    total_reg = sum(s["by_method"]["baseReg"]["rows"] for s in summaries)
    total_mlp = sum(s["by_method"]["baseMLP"]["rows"] for s in summaries)
    result = {
        "scope": "Reachability inventory of released scPerturBench cellular-context result tables; no corrected predictions or leaderboard are computed.",
        "reproducibility_repository_commit": COMMIT,
        "files": summaries,
        "totals": {"affected_baseline_rows": total_target, "baseReg_rows": total_reg, "baseMLP_rows": total_mlp},
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "commit": COMMIT,
        "totals": result["totals"],
        "files": [{"name": s["name"], "rows_total": s["rows_total"], "method_column": s["method_column"],
                   "affected_baseline_rows": s["affected_baseline_rows"], "columns": s["columns"],
                   "by_method": s["by_method"]} for s in summaries],
    }, indent=2))
    print("PASS: all four released cellular-context result files are hash verified and contain baseReg/baseMLP rows.")

if __name__ == "__main__":
    main()
