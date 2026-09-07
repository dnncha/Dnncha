"""Fetch only the three public, pinned inputs; reject a changed Git blob."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

COMMIT = '0c68f87d554a52e363dbfda2a9d1fa9538eeae9f'
FILES = {
    'evaluation_pipelines/classification/classification_metrics.Rmd': '17c590896591752be5a06098ddf2ac2ac248d419',
    'data/classification/demo_result/query.csv': '68a5f15043381bb9af30fa6af4170a44dea35143',
    'data/classification/demo_result/predict.csv': 'dbc586d1e79902bcfa62c5f4521ed85c64bf3806',
}
root = Path(__file__).resolve().parent / 'inputs'
root.mkdir(exist_ok=True)
manifest = []
for path, expected in FILES.items():
    url = f'https://raw.githubusercontent.com/PYangLab/scMultiBench/{COMMIT}/{path}'
    target = root / Path(path).name
    if target.exists():
        raw = target.read_bytes()
    else:
        with urlopen(Request(url, headers={'User-Agent': 'CheerfulDuck-scientific-code-audit'}), timeout=40) as response:
            raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError(f'Oversized input: {path}')
    actual = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
    if actual != expected:
        raise ValueError(f'Git blob mismatch: {path}: {actual} != {expected}')
    target.write_bytes(raw)
    manifest.append({'path': path, 'url': url, 'git_blob_sha1': actual,
                     'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
(root / 'manifest.json').write_text(json.dumps({'commit': COMMIT, 'files': manifest}, indent=2) + '\n')
print('Verified all three complete upstream blobs.')
