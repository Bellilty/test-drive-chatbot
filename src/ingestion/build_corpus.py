from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

# Ensure project root on path when run as a script
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import (  # noqa: E402
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNKS_JSON,
    MAX_PARAGRAPH_LEN,
    MIN_PARAGRAPH_LEN,
    PROCESSED_DIR,
    RAW_DIR,
)


def load_raw_documents(raw_dir: Path | None = None) -> list[dict]:
    raw_dir = raw_dir or RAW_DIR
    docs: list[dict] = []
    for path in raw_dir.glob("*.txt"):
        data = json.loads(path.read_text(encoding="utf-8"))
        docs.append(
            {
                "slug": path.stem,
                "title": data.get("title", ""),
                "url": data.get("url"),
                "paragraphs": data.get("paragraphs", []),
            }
        )
    return docs


def split_paragraph(paragraph: str, max_len: int, overlap: int) -> list[str]:
    if len(paragraph) <= max_len:
        return [paragraph]
    chunks: list[str] = []
    start = 0
    while start < len(paragraph):
        end = start + max_len
        chunk = paragraph[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(paragraph):
            break
    return chunks


def detect_model_name(title: str) -> str | None:
    match = re.search(r"([A-Za-zא-ת0-9-]+)", title)
    return match.group(1) if match else None


def build_chunks(docs: Iterable[dict]) -> list[dict]:
    chunks: list[dict] = []
    chunk_id = 0
    for doc in docs:
        title = doc.get("title", "")
        url_guess = doc.get("url")
        paragraphs = doc.get("paragraphs", [])
        model_name = detect_model_name(title)
        buffer = ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) < MIN_PARAGRAPH_LEN:
                buffer = (buffer + " " + paragraph).strip()
                continue
            if buffer:
                paragraph = buffer + " " + paragraph
                buffer = ""
            if len(paragraph) > MAX_PARAGRAPH_LEN:
                parts = split_paragraph(paragraph, CHUNK_SIZE, CHUNK_OVERLAP)
            else:
                parts = [paragraph]
            for part in parts:
                chunk_id += 1
                chunks.append(
                    {
                        "chunk_id": f"chunk-{chunk_id}",
                        "article_title": title,
                        "article_url": url_guess,
                        "car_model": model_name,
                        "chunk_text": part.strip(),
                    }
                )
        if buffer:
            chunk_id += 1
            chunks.append(
                {
                    "chunk_id": f"chunk-{chunk_id}",
                    "article_title": title,
                    "article_url": url_guess,
                    "car_model": model_name,
                    "chunk_text": buffer.strip(),
                }
            )
    return chunks


def persist_chunks(chunks: list[dict]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_JSON.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    docs = load_raw_documents()
    chunks = build_chunks(docs)
    persist_chunks(chunks)
    avg_len = sum(len(c["chunk_text"]) for c in chunks) / len(chunks) if chunks else 0
    print(f"Built {len(chunks)} chunks. Avg length: {avg_len:.1f} chars")


if __name__ == "__main__":
    main()

