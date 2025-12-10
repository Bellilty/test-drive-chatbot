from __future__ import annotations

import re
from typing import List, Tuple

import faiss
import numpy as np

from src.config import TOP_K
from src.rag.embeddings import embed_texts
from src.rag.vector_store import load_index, load_metadata


def extract_candidate_models(metadata: list[dict]) -> set[str]:
    models = set()
    for item in metadata:
        title = item.get("article_title") or ""
        car_model = item.get("car_model")
        if car_model:
            models.add(car_model)
        for token in re.findall(r"[A-Za-zא-ת0-9-]+", title):
            if len(token) > 2:
                models.add(token)
    return models


def detect_models_in_query(query: str, models: set[str]) -> set[str]:
    hits = set()
    for model in models:
        if model.lower() in query.lower():
            hits.add(model)
    return hits


def filter_metadata_by_models(metadata: list[dict], models: set[str]) -> list[int]:
    if not models:
        return list(range(len(metadata)))
    indices = []
    for idx, item in enumerate(metadata):
        if any(model.lower() in (item.get("article_title", "").lower()) for model in models) or (
            item.get("car_model") and item["car_model"].lower() in [m.lower() for m in models]
        ):
            indices.append(idx)
    return indices


def retrieve(query: str, top_k: int = TOP_K) -> List[Tuple[dict, float]]:
    metadata = load_metadata()
    index: faiss.Index = load_index()
    models = extract_candidate_models(metadata)
    hits = detect_models_in_query(query, models)
    allowed_indices = filter_metadata_by_models(metadata, hits)

    query_vec = embed_texts([query]).astype(np.float32)
    distances, idxs = index.search(query_vec, top_k if not allowed_indices else len(allowed_indices))

    results: List[Tuple[dict, float]] = []
    for dist, idx in zip(distances[0], idxs[0]):
        if idx == -1:
            continue
        if allowed_indices and idx not in allowed_indices:
            continue
        results.append((metadata[idx], float(dist)))
        if len(results) >= top_k:
            break
    return results

