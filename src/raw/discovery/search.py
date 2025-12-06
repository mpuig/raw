"""Search functionality for RAW tools.

Supports two search modes:
- Semantic search using sentence-transformers (if installed)
- TF-IDF fallback for keyword matching

Install semantic search: uv add raw[search]
"""

import hashlib
import json
import re
from collections import Counter
from math import log, sqrt
from pathlib import Path
from typing import Any

import numpy as np

from raw.scaffold.init import get_tools_dir, load_tool_config

# Semantic search availability
_SEMANTIC_AVAILABLE = False
_model = None

try:
    from sentence_transformers import SentenceTransformer

    _SEMANTIC_AVAILABLE = True
except ImportError:
    pass


def _get_model() -> Any:
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None and _SEMANTIC_AVAILABLE:
        _model = SentenceTransformer("intfloat/e5-base-v2")
    return _model


def _get_cache_dir(project_dir: Path | None = None) -> Path:
    """Get the cache directory for embeddings."""
    base = project_dir or Path.cwd()
    cache_dir = base / ".raw" / "cache" / "embeddings"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _compute_content_hash(tools_data: list[dict[str, Any]]) -> str:
    """Compute hash of tools content to detect changes."""
    content = json.dumps(
        [(t["name"], t["description"], t["searchable_text"]) for t in tools_data],
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _load_cached_embeddings(cache_dir: Path, content_hash: str) -> np.ndarray | None:
    """Load cached embeddings if they exist and match content hash."""
    cache_file = cache_dir / f"tools_{content_hash}.npy"
    if cache_file.exists():
        try:
            return np.load(cache_file)
        except Exception:
            pass
    return None


def _save_cached_embeddings(cache_dir: Path, content_hash: str, embeddings: np.ndarray) -> None:
    """Save embeddings to cache."""
    cache_file = cache_dir / f"tools_{content_hash}.npy"
    try:
        np.save(cache_file, embeddings)
    except Exception:
        pass


def _semantic_search(
    query: str, tools_data: list[dict[str, Any]], project_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Search using semantic embeddings."""
    model = _get_model()
    if model is None:
        return []

    cache_dir = _get_cache_dir(project_dir)
    content_hash = _compute_content_hash(tools_data)

    tool_embeddings = _load_cached_embeddings(cache_dir, content_hash)
    if tool_embeddings is None:
        texts = [f"passage: {t['name']}. {t['description']}" for t in tools_data]
        tool_embeddings = model.encode(texts, normalize_embeddings=True)
        _save_cached_embeddings(cache_dir, content_hash, tool_embeddings)

    query_embedding = model.encode([f"query: {query}"], normalize_embeddings=True)[0]

    similarities = np.dot(tool_embeddings, query_embedding)

    results = []
    for i, tool in enumerate(tools_data):
        score = float(similarities[i])
        if score > 0.1:
            results.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "version": tool["version"],
                    "status": tool["status"],
                    "path": tool["path"],
                    "score": score,
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    text = text.lower()
    words = re.findall(r"\b\w+\b", text)
    return words


def compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency for a list of tokens."""
    total_terms = len(tokens)
    if total_terms == 0:
        return {}

    term_counts = Counter(tokens)
    return {term: count / total_terms for term, count in term_counts.items()}


def compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency across all documents."""
    num_documents = len(documents)
    if num_documents == 0:
        return {}

    doc_frequency: dict[str, int] = {}
    for doc_tokens in documents:
        unique_terms = set(doc_tokens)
        for term in unique_terms:
            doc_frequency[term] = doc_frequency.get(term, 0) + 1

    idf = {}
    for term, freq in doc_frequency.items():
        idf[term] = log(num_documents / freq)

    return idf


def compute_tfidf(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF scores."""
    tfidf = {}
    for term, tf_score in tf.items():
        idf_score = idf.get(term, 0)
        tfidf[term] = tf_score * idf_score
    return tfidf


def cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    """Compute cosine similarity between two TF-IDF vectors."""
    all_terms = set(vec1.keys()) | set(vec2.keys())
    dot_product = sum(vec1.get(term, 0) * vec2.get(term, 0) for term in all_terms)
    mag1 = sqrt(sum(score**2 for score in vec1.values()))
    mag2 = sqrt(sum(score**2 for score in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot_product / (mag1 * mag2)


def _tfidf_search(query: str, tools_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Search using TF-IDF similarity."""
    query_tokens = tokenize(query)
    doc_tokens_list = [tokenize(tool["searchable_text"]) for tool in tools_data]

    all_docs = [query_tokens] + doc_tokens_list
    idf = compute_idf(all_docs)

    query_tf = compute_tf(query_tokens)
    query_tfidf = compute_tfidf(query_tf, idf)

    results = []
    for tool, doc_tokens in zip(tools_data, doc_tokens_list, strict=True):
        doc_tf = compute_tf(doc_tokens)
        doc_tfidf = compute_tfidf(doc_tf, idf)

        similarity = cosine_similarity(query_tfidf, doc_tfidf)

        if similarity > 0:
            results.append(
                {
                    "name": tool["name"],
                    "description": tool["description"],
                    "version": tool["version"],
                    "status": tool["status"],
                    "path": tool["path"],
                    "score": similarity,
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def search_tools(query: str, project_dir: Path | None = None) -> list[dict[str, Any]]:
    """Search for tools using semantic similarity (with TF-IDF fallback).

    Uses sentence-transformers with e5-base-v2 if available, otherwise
    falls back to TF-IDF keyword matching.

    Args:
        query: Search query string
        project_dir: Project directory (defaults to cwd)

    Returns:
        List of tool results with relevance scores, sorted by score descending
    """
    tools_dir = get_tools_dir(project_dir)

    if not tools_dir.exists():
        return []

    tools_data = []
    for tool_path in sorted(tools_dir.iterdir()):
        if not tool_path.is_dir():
            continue

        config = load_tool_config(tool_path)
        if not config:
            continue

        searchable_text = f"{config.name} {config.name} {config.name} {config.description}"

        config_path = tool_path / "config.yaml"
        if config_path.exists():
            try:
                config_content = config_path.read_text()
                searchable_text += f" {config_content}"
            except Exception:
                pass

        tools_data.append(
            {
                "name": config.name,
                "description": config.description,
                "version": config.version,
                "status": config.status,
                "path": str(tool_path),
                "searchable_text": searchable_text,
            }
        )

    if not tools_data:
        return []

    if _SEMANTIC_AVAILABLE:
        return _semantic_search(query, tools_data, project_dir)
    else:
        return _tfidf_search(query, tools_data)


def is_semantic_available() -> bool:
    """Check if semantic search is available."""
    return _SEMANTIC_AVAILABLE
