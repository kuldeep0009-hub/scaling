import json
import math
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

INDEX_PATH = Path("data/index.json")
TOKEN_RE = re.compile(r"[^a-z0-9+#.\s-]+")
EMBEDDING_URL = "https://api.openai.com/v1/embeddings"


def tokenize(text: str) -> list[str]:
    cleaned = TOKEN_RE.sub(" ", (text or "").lower())
    return [token for token in cleaned.split() if len(token) > 2]


def build_index(documents: list[dict[str, str]]) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    for doc in documents:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", doc["text"]) if part.strip()]
        for idx, paragraph in enumerate(paragraphs):
            tokens = tokenize(paragraph)
            if not tokens:
                continue
            tf: dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            chunks.append(
                {
                    "id": f"{doc['id']}-{idx}",
                    "title": doc["title"],
                    "source": doc["source"],
                    "text": paragraph[:1800],
                    "token_count": len(tokens),
                    "term_frequency": tf,
                }
            )
    return {"chunks": chunks}


def attach_embeddings(index: dict[str, Any], vectors: list[list[float]]) -> dict[str, Any]:
    chunks = index.get("chunks", [])
    if len(chunks) != len(vectors):
        raise ValueError("Embedding count must match chunk count.")
    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector
    index["embedding_provider"] = os.getenv("EMBEDDING_PROVIDER", "openai")
    index["embedding_model"] = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    return index


def load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"chunks": []}
    return json.loads(INDEX_PATH.read_text())


def retrieve(query: str, limit: int = 6) -> list[dict[str, Any]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    index = load_index()
    query_embedding = embed_query(query) if index_has_embeddings(index) else None
    scored = []
    lexical_scores = []
    semantic_scores = []
    raw = []

    for chunk in index.get("chunks", []):
        tf = chunk.get("term_frequency", {})
        lexical = sum(tf.get(token, 0) for token in query_tokens) / math.sqrt(chunk.get("token_count", 1))
        semantic = cosine_similarity(query_embedding, chunk.get("embedding")) if query_embedding else 0.0
        lexical_scores.append(lexical)
        semantic_scores.append(semantic)
        raw.append((chunk, lexical, semantic))

    max_lexical = max(lexical_scores, default=0) or 1
    min_semantic = min(semantic_scores, default=0)
    max_semantic = max(semantic_scores, default=0)
    semantic_range = max(max_semantic - min_semantic, 1e-9)

    for chunk, lexical, semantic in raw:
        lexical_norm = lexical / max_lexical
        semantic_norm = (semantic - min_semantic) / semantic_range if query_embedding else 0
        score = 0.45 * lexical_norm + 0.55 * semantic_norm if query_embedding else lexical_norm
        if score > 0:
            scored.append({**chunk, "score": score, "lexical_score": lexical, "semantic_score": semantic})
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def index_has_embeddings(index: dict[str, Any]) -> bool:
    return any(chunk.get("embedding") for chunk in index.get("chunks", []))


def embed_query(text: str) -> list[float] | None:
    if os.getenv("EMBEDDING_PROVIDER", "openai") != "openai":
        return None
    api_key = os.getenv("OPENAI_EMBEDDING_API_KEY", "")
    if not api_key:
        return None
    try:
        return embed_texts([text], api_key=api_key, model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))[0]
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError):
        return None


def embed_texts(texts: list[str], api_key: str, model: str, batch_size: int = 64) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        payload = json.dumps({"model": model, "input": batch}).encode("utf-8")
        request = Request(
            EMBEDDING_URL,
            data=payload,
            headers={
                "authorization": f"Bearer {api_key}",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        vectors.extend(item["embedding"] for item in sorted(data["data"], key=lambda item: item["index"]))
    return vectors


def cosine_similarity(left: list[float] | None, right: list[float] | None) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def evidence_block(chunks: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[{idx}] {chunk['title']} ({chunk['source']})\n{chunk['text']}"
        for idx, chunk in enumerate(chunks, start=1)
    )
