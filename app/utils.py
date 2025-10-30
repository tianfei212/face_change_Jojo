import os
import pathlib
import sys
from typing import Iterable

import requests

from .config import settings, ASSETS_DIR, MODELS_DIR


def ensure_dir(path: str) -> None:
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def _download(url: str, dst_path: str) -> None:
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 // total
                    print(f"Downloading {os.path.basename(dst_path)}: {percent}%", file=sys.stderr)


def download_models(urls: Iterable[tuple[str, str]]) -> None:
    ensure_dir(str(ASSETS_DIR))
    ensure_dir(settings.models_dir)
    for filename, url in urls:
        dst = os.path.join(settings.models_dir, filename)
        if os.path.exists(dst):
            continue
        print(f"Model missing: {filename}, downloading from {url}")
        _download(url, dst)