import asyncio
import zlib
from types import SimpleNamespace

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from pharmag.index import Index, OpenAIEmbedder, embedding_text
from pharmag.models import Chunk

DIMS = 32


class FakeEmbedder:
    """Bag of hashed tokens: equal texts give equal vectors, shared words give similar ones."""

    async def embed(self, texts):
        out = np.zeros((len(texts), DIMS), dtype=np.float32)
        for row, text in enumerate(texts):
            for token in text.lower().split():
                out[row, zlib.crc32(token.encode()) % DIMS] += 1
        return out


class SameVectorEmbedder:
    """Every text gets the same vector, so the dense ranking is chunk order."""

    async def embed(self, texts):
        return np.ones((len(texts), DIMS), dtype=np.float32)


def run(coro):
    return asyncio.run(coro)


WORDS = ["warfarin", "inr", "egfr", "cyp3a4", "dose", "renal", "bleeding", "liver", "tablet", "eliquis"]
DRUGS = [None, "warfarin", "apixaban", "metformin"]
SECTIONS = [None, "dosage", "contraindications"]

words = st.sampled_from(WORDS)


@st.composite
def chunks_st(draw, min_size=1, max_size=12):
    n = draw(st.integers(min_size, max_size))
    out = []
    for i in range(n):
        drug = draw(st.sampled_from(DRUGS))
        out.append(
            Chunk(
                id=f"f.md#L{i}-{i}",
                file="f.md",
                drug=drug,
                source="glossary" if drug is None else draw(st.sampled_from(["dailymed", "medlineplus"])),
                section=draw(st.sampled_from(SECTIONS)),
                heading_path=tuple(draw(st.lists(words, min_size=1, max_size=3))),
                line_start=i,
                line_end=i,
                text=" ".join(draw(st.lists(words, min_size=1, max_size=8))),
            )
        )
    return out


queries = st.lists(words, min_size=1, max_size=4).map(" ".join)
filters = st.fixed_dictionaries(
    {},
    optional={
        "drug": st.sampled_from(DRUGS[1:]),
        "source": st.sampled_from(["dailymed", "medlineplus", "glossary"]),
        "section": st.sampled_from(SECTIONS[1:]),
    },
)


def build(chunks, embedder=None):
    return run(Index.build(chunks, embedder or FakeEmbedder()))


def search(index, query, **kwargs):
    return run(index.search(query, **kwargs))


@given(chunks_st(), queries, filters)
def test_every_hit_satisfies_every_filter(chunks, query, flt):
    for hit in search(build(chunks), query, k=50, **flt):
        for field, value in flt.items():
            assert getattr(hit.chunk, field) == value


@given(chunks_st(), queries, st.integers(0, 15), filters)
def test_at_most_k_distinct_hits_in_non_increasing_score_order(chunks, query, k, flt):
    hits = search(build(chunks), query, k=k, **flt)
    assert len(hits) <= k
    ids = [h.chunk.id for h in hits]
    assert len(ids) == len(set(ids))
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


@given(chunks_st(), queries)
def test_first_in_both_rankings_is_first_overall(chunks, query):
    hits = search(build(chunks), query, k=len(chunks))
    both = [h for h in hits if h.dense_rank == 1 and h.bm25_rank == 1]
    if both:
        assert hits[0] is both[0]


@given(chunks_st())
def test_searching_a_chunks_own_text_returns_it_first(chunks):
    texts = [embedding_text(c) for c in chunks]
    vectors = run(FakeEmbedder().embed(texts))
    # hashed bags of tokens collide for texts that are permutations of each other
    if len({v.tobytes() for v in vectors}) < len(chunks):
        return
    index = build(chunks)
    for chunk, text in zip(chunks, texts):
        assert search(index, text, k=1)[0].chunk is chunk


@given(chunks_st())
def test_stored_rows_have_unit_length(chunks):
    norms = np.linalg.norm(build(chunks)._vectors, axis=1)
    np.testing.assert_allclose(norms, 1.0, rtol=1e-5)


@given(chunks_st(), queries, filters)
def test_building_twice_gives_equal_results(chunks, query, flt):
    assert search(build(chunks), query, **flt) == search(build(chunks), query, **flt)


def stub_client(calls):
    """Answers each batch with rows in reverse order and after a delay that makes batches finish out of order."""

    async def create(*, input, model):
        calls.append(len(input))
        await asyncio.sleep(0.001 * (len(calls) % 3))
        rows = [SimpleNamespace(index=i, embedding=[float(len(t)), float(sum(map(ord, t)))]) for i, t in enumerate(input)]
        return SimpleNamespace(data=rows[::-1])

    return SimpleNamespace(embeddings=SimpleNamespace(create=create))


@given(st.lists(st.text(max_size=6), max_size=40), st.integers(1, 10), st.integers(1, 5))
@settings(deadline=None)
def test_openai_embedder_keeps_input_order(texts, batch_size, concurrency):
    calls = []
    embedder = OpenAIEmbedder(stub_client(calls), "m", batch_size=batch_size, concurrency=concurrency)
    got = run(embedder.embed(texts))
    expected = [[float(len(t)), float(sum(map(ord, t)))] for t in texts]
    assert got.dtype == np.float32
    assert got.tolist() == expected
    assert all(n <= batch_size for n in calls)


def chunk(i, text, drug="warfarin"):
    return Chunk(f"f#L{i}", "f", drug, "dailymed", "dosage", ("Dosage",), i, i, text)


def test_a_rare_exact_token_wins_even_when_dense_does_not_help():
    chunks = [chunk(i, "general dosing advice") for i in range(8)] + [chunk(8, "avoid with CYP3A4 inhibitors")]
    index = build(chunks, SameVectorEmbedder())
    hits = search(index, "CYP3A4", k=3)
    assert hits[0].chunk is chunks[8]
    assert hits[0].bm25_rank == 1
    assert hits[0].dense_rank == 9


def test_a_drug_filter_excludes_other_drugs():
    chunks = [chunk(0, "dose", "warfarin"), chunk(1, "dose", "apixaban"), chunk(2, "dose", "warfarin")]
    hits = search(build(chunks), "dose", drug="apixaban")
    assert [h.chunk.id for h in hits] == ["f#L1"]


def test_no_candidates_gives_an_empty_list():
    assert search(build([chunk(0, "dose")]), "dose", drug="metformin") == []


def test_a_query_with_no_lexical_overlap_has_no_bm25_rank():
    hits = search(build([chunk(0, "dose")]), "zzz")
    assert hits[0].bm25_rank is None
    assert hits[0].score == 1 / 61
