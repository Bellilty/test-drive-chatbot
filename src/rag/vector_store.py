from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import faiss

from src.config import INDEX_METADATA, INDEX_PATH


def load_index(index_path: Path | None = None) -> faiss.IndexFlatL2:
    index_path = index_path or INDEX_PATH
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found at {index_path}. Run ingestion first.")
    return faiss.read_index(str(index_path))


def load_metadata(metadata_path: Path | None = None) -> list[dict]:
    metadata_path = metadata_path or INDEX_METADATA
    if not metadata_path.exists():
        raise FileNotFoundError(f"Metadata not found at {metadata_path}. Run ingestion first.")
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def save_index(index: faiss.IndexFlatL2, chunks: list[dict], index_path: Optional[Path] = None, metadata_path: Optional[Path] = None) -> None:
    index_path = index_path or INDEX_PATH
    metadata_path = metadata_path or INDEX_METADATA
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    metadata_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

