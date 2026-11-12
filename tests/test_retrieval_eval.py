import asyncio
import tempfile
import zlib
from pathlib import Path

import numpy as np
from embedding_cache import CachingEmbedder
from hypothesis import given, settings
from hypothesis import strategies as st
from retrieval_eval import baseline_chunks, fixed_windows

from pharmag.corpus import load_corpus

CORPUS = Path(__file__).parent.parent / "corpus"

# Short texts over a tiny alphabet with many newlines, and small sizes, give many windows and line breaks.
texts = st.text(alphabet="ab\n", max_size=300)


@st.composite
def window_args(draw):
    size = draw(st.integers(1, 40))
    return draw(texts), size, draw(st.integers(0, size - 1))


@given(window_args())
def test_every_character_is_in_a_window(args):
    text, size, overlap = args
    covered = {i for w in fixed_windows(text, size, overlap) for i in range(w.start, w.end)}
    assert covered == set(range(len(text)))


@given(window_args())
def test_no_window_is_empty_or_longer_than_the_size(args):
    text, size, overlap = args
    for w in fixed_windows(text, size, overlap):
        assert 0 < w.end - w.start <= size


@given(window_args())
def test_consecutive_windows_overlap_by_exactly_the_overlap(args):
    text, size, overlap = args
    ws = fixed_windows(text, size, overlap)
    for a, b in zip(ws, ws[1:]):
        assert a.end - b.start == overlap
        assert b.end > a.end


@given(window_args())
def test_the_line_range_is_the_lines_the_characters_touch(args):
    text, size, overlap = args
    line_of, line = [], 1
    for ch in text:
        line_of.append(line)
        line += ch == "\n"  # a newline belongs to the line it ends
    for w in fixed_windows(text, size, overlap):
        touched = set(line_of[w.start : w.end])
        assert set(range(w.line_start, w.line_end + 1)) == touched


def test_baseline_chunks_sit_on_the_parsers_lines_and_keep_its_labels():
    ours = load_corpus(CORPUS)
    baseline = baseline_chunks(CORPUS, ours)
    assert len({c.id for c in baseline}) == len(baseline)
    parsed = {c.file: c for c in ours}
    assert {c.file for c in baseline} == set(parsed)
    for c in baseline:
        lines = (CORPUS / c.file).read_bytes().decode("utf-8").split("\n")
        named = "".join(f"{line}\n" for line in lines[c.line_start - 1 : c.line_end])
        assert c.text in named
        assert (c.drug, c.source) == (parsed[c.file].drug, parsed[c.file].source)
        assert c.section is None and c.heading_path == ()


class CountingEmbedder:
    def __init__(self):
        self.received: list[str] = []

    async def embed(self, texts):
        self.received += texts
        return np.array([[zlib.crc32(t.encode()), len(t)] for t in texts], dtype=np.float32)


@settings(deadline=None)
@given(st.lists(st.text(max_size=20), max_size=8))
def test_the_cache_returns_the_wrapped_rows_and_sends_each_text_once(batch):
    with tempfile.TemporaryDirectory() as d:
        inner = CountingEmbedder()
        cached = CachingEmbedder(inner, "m", Path(d))
        first = asyncio.run(cached.embed(batch))
        second = asyncio.run(cached.embed(batch))
        expected = asyncio.run(CountingEmbedder().embed(batch))
        assert np.array_equal(first, expected) and np.array_equal(second, expected)
        assert inner.received == list(dict.fromkeys(batch))


@settings(deadline=None)
@given(st.lists(st.text(max_size=20), min_size=1, max_size=8))
def test_a_different_model_does_not_reuse_stored_vectors(batch):
    with tempfile.TemporaryDirectory() as d:
        asyncio.run(CachingEmbedder(CountingEmbedder(), "model-a", Path(d)).embed(batch))
        other = CountingEmbedder()
        asyncio.run(CachingEmbedder(other, "model-b", Path(d)).embed(batch))
        assert other.received == list(dict.fromkeys(batch))
