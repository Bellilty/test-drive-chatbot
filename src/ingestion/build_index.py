from __future__ import annotations

import json
import sys
from pathlib import Path

import faiss
import numpy as np

# Ensure project root on path when run as a script
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import CHUNKS_JSON, INDEX_DIR, INDEX_METADATA, INDEX_PATH  # noqa: E402
from src.rag.embeddings import embed_texts  # noqa: E402


def load_chunks() -> list[dict]:
    return json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))


def build_index(chunks: list[dict]) -> tuple[faiss.IndexFlatL2, np.ndarray]:
    texts = [c["chunk_text"] for c in chunks]
    embeddings = embed_texts(texts)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings.astype(np.float32))
    return index, embeddings


def persist_index(index: faiss.IndexFlatL2, chunks: list[dict]) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    INDEX_METADATA.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    chunks = load_chunks()
    if not chunks:
        raise ValueError("No chunks found; run build_corpus first.")
    index, _ = build_index(chunks)
    persist_index(index, chunks)
    print(f"Index built with {index.ntotal} vectors.")


if __name__ == "__main__":
    main()

