import hashlib
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from pharmag.index import Embedder


class CachingEmbedder:
    """Development cache around any Embedder: one .npy file per text, named by a hash of model and text."""

    def __init__(self, inner: Embedder, model: str, directory: Path) -> None:
        self._inner = inner
        self._model = model
        self._directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.sent = 0  # texts passed to the inner embedder so far

    def _path(self, text: str) -> Path:
        key = hashlib.sha256(f"{self._model}\0{text}".encode()).hexdigest()
        return self._directory / f"{key}.npy"

    async def embed(self, texts: Sequence[str]) -> np.ndarray:
        misses = list(dict.fromkeys(t for t in texts if not self._path(t).exists()))
        if misses:
            for text, row in zip(misses, await self._inner.embed(misses), strict=True):
                np.save(self._path(text), row)
            self.sent += len(misses)
        return np.array([np.load(self._path(t)) for t in texts], dtype=np.float32)
