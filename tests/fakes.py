import zlib

import numpy as np

DIMS = 32


class FakeEmbedder:
    """Bag of hashed tokens: equal texts give equal vectors, shared words give similar ones."""

    async def embed(self, texts):
        out = np.zeros((len(texts), DIMS), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in text.lower().split():
                out[row, zlib.crc32(token.encode()) % DIMS] += 1
        return out
