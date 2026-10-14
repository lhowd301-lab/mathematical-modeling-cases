"""Verify and unpack the losslessly compressed contest data."""
from pathlib import Path
import gzip
import hashlib
import json

root = Path(__file__).resolve().parent
data_dir = root / "paper_output/data_cleaned"
for item in json.loads((root / "dataset_manifest.json").read_text(encoding="utf-8")):
    path = data_dir / item["file"]
    if path.exists():
        data = path.read_bytes()
    else:
        data = gzip.decompress(path.with_suffix(path.suffix + ".gz").read_bytes())
    if hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise RuntimeError("Data checksum mismatch: " + item["file"])
    if not path.exists():
        path.write_bytes(data)
    print(item["file"], "OK")
