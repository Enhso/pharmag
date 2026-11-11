import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import bm25s
import numpy as np
from openai import AsyncOpenAI

from pharmag.models import Chunk

RRF_K = 60


def embedding_text(chunk: Chunk) -> str:
    """Header from metadata, a blank line, then the passage. Both the embedder and BM25 read this."""
    header = f"{chunk.drug or 'glossary'} | {chunk.source} | {' > '.join(chunk.heading_path)}"
    return f"{header}\n\n{chunk.text}"


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Embedder(Protocol):
    async def embed(self, texts: Sequence[str]) -> np.ndarray:
        """Float32 array with one row per text, in input order."""
        ...


class OpenAIEmbedder:
    def __init__(
        self, client: AsyncOpenAI, model: str, *, batch_size: int = 128, concurrency: int = 4
    ) -> None:
        self._client = client
        self._model = model
        self._batch_size = batch_size
        self._slots = asyncio.Semaphore(concurrency)

    async def embed(self, texts: Sequence[str]) -> np.ndarray:
        batches = [texts[i : i + self._batch_size] for i in range(0, len(texts), self._batch_size)]
        rows = await asyncio.gather(*(self._embed_batch(b) for b in batches))
        return np.array([row for batch in rows for row in batch], dtype=np.float32)

    async def _embed_batch(self, batch: Sequence[str]) -> list[list[float]]:
        async with self._slots:
            response = await self._client.embeddings.create(input=list(batch), model=self._model)
        # the API tags each row with its input position, so sort rather than trust the order
        return [d.embedding for d in sorted(response.data, key=lambda d: d.index)]


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float
    dense_rank: int  # 1-based among the candidates
    bm25_rank: int | None  # None when the chunk shares no token with the query


class Index:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder: Embedder) -> None:
        self._chunks = chunks
        self._vectors = vectors
        self._embedder = embedder
        self._bm25 = bm25s.BM25()
        self._bm25.index([tokenize(embedding_text(c)) for c in chunks], show_progress=False)

    @classmethod
    async def build(cls, chunks: Sequence[Chunk], embedder: Embedder) -> "Index":
        chunks = list(chunks)
        vectors = await embedder.embed([embedding_text(c) for c in chunks])
        vectors = vectors.astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return cls(chunks, vectors / np.where(norms == 0, 1, norms), embedder)

    async def search(
        self,
        query: str,
        *,
        k: int = 6,
        drug: str | None = None,
        source: str | None = None,
        section: str | None = None,
    ) -> list[Hit]:
        wanted = {"drug": drug, "source": source, "section": section}
        candidates = [
            i
            for i, c in enumerate(self._chunks)
            if all(v is None or getattr(c, f) == v for f, v in wanted.items())
        ]
        if not candidates:
            return []

        query_vector = (await self._embedder.embed([query]))[0]
        norm = np.linalg.norm(query_vector)
        query_vector = query_vector / (norm or 1)
        similarity = self._vectors[candidates] @ query_vector
        # stable sort on the negated score keeps chunk order among equal scores
        dense_order = [candidates[j] for j in np.argsort(-similarity, kind="stable")]
        dense_rank = {i: r for r, i in enumerate(dense_order, 1)}

        bm25_rank: dict[int, int] = {}
        query_tokens = tokenize(query)
        if query_tokens:
            scores = self._bm25.get_scores(query_tokens)
            positive = [i for i in candidates if scores[i] > 0]
            positive.sort(key=lambda i: (-scores[i], i))
            bm25_rank = {i: r for r, i in enumerate(positive, 1)}

        def fused(i: int) -> float:
            score = 1 / (RRF_K + dense_rank[i])
            if i in bm25_rank:
                score += 1 / (RRF_K + bm25_rank[i])
            return score

        best = sorted(candidates, key=lambda i: (-fused(i), i))[:k]
        return [Hit(self._chunks[i], fused(i), dense_rank[i], bm25_rank.get(i)) for i in best]
