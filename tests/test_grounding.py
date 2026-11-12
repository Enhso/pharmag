from pathlib import Path

from hypothesis import assume, given
from hypothesis import strategies as st

from pharmag.corpus import load_corpus
from pharmag.grounding import (
    dangling_markers,
    drop_dangling,
    failed_claims,
    markers,
    normalize,
    quote_occurs,
)
from pharmag.models import Citation, Claim, Draft

CHUNKS = load_corpus(Path(__file__).parent.parent / "corpus")
PASSAGES = [c.text for c in CHUNKS]

whitespace = st.text(alphabet=" \t\n ", min_size=1, max_size=4)
word = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8)
numbers = st.integers(min_value=1, max_value=30)


@st.composite
def span_of_a_passage(draw):
    passage = draw(st.sampled_from(PASSAGES))
    a = draw(st.integers(0, len(passage) - 1))
    b = draw(st.integers(a + 1, len(passage)))
    return passage, passage[a:b]


@given(span_of_a_passage(), st.lists(whitespace, min_size=40, max_size=40), st.sampled_from(["keep", "upper", "lower"]))
def test_any_span_of_a_passage_passes_after_reflow_and_case_change(drawn, gaps, case):
    passage, span = drawn
    assume(normalize(span))
    pieces = iter(gaps * 100)
    reflowed = "".join(next(pieces) if ch.isspace() else ch for ch in span)
    quote = {"keep": reflowed, "upper": reflowed.upper(), "lower": reflowed.lower()}[case]
    assert quote_occurs(quote, passage)


@given(span_of_a_passage(), st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12))
def test_a_quote_with_a_token_absent_from_the_passage_fails(drawn, token):
    passage, span = drawn
    assume(token not in normalize(passage))
    assert not quote_occurs(f"{span} {token}", passage)
    assert not quote_occurs(token, passage)


def test_an_empty_quote_never_occurs():
    assert not quote_occurs("", "anything") and not quote_occurs(" ** ", "anything")


@given(st.lists(st.one_of(word, st.lists(numbers, min_size=1, max_size=3)), max_size=12), st.booleans())
def test_markers_returns_the_numbers_written_into_the_prose_in_order(parts, comma_style):
    prose, expected = "", []
    for part in parts:
        if isinstance(part, str):
            prose += part + " "
        elif comma_style:
            prose += "[" + ", ".join(map(str, part)) + "] "
            expected += part
        else:
            prose += "".join(f"[{n}]" for n in part) + " "
            expected += part
    assert markers(prose) == expected


sentence = st.tuples(st.lists(word, min_size=1, max_size=5), st.lists(numbers, max_size=2))


@given(st.lists(sentence, max_size=8), st.sets(numbers, max_size=10))
def test_drop_dangling_leaves_no_dangling_marker_and_keeps_every_clean_sentence(sentences, surviving):
    rendered = [" ".join(words) + "".join(f" [{n}]" for n in nums) + "." for words, nums in sentences]
    result = drop_dangling(" ".join(rendered), surviving)
    assert dangling_markers(result, surviving) == []
    for text, (_, nums) in zip(rendered, sentences):
        if all(n in surviving for n in nums):
            assert text in result


def test_markers_after_the_final_punctuation_go_with_their_sentence():
    prose = "A is true [1]. B is a rare but serious illness. [1][2] C is fine [1]."
    assert drop_dangling(prose, {1}) == "A is true [1]. C is fine [1]."
    assert drop_dangling("A [1]. B. [1] [3] C [1].", {1}) == "A [1]. C [1]."


def test_failed_claims_names_each_kind_of_failure():
    chunk = CHUNKS[0]
    evidence = {chunk.id: chunk}
    good = " ".join(chunk.text.split()[:5])
    cite = lambda cid, quote: Claim(text="x", kind="fact", citations=[Citation(chunk_id=cid, quote=quote)])  # noqa: E731
    draft = Draft(
        answer="",
        claims=[
            cite(chunk.id, good),
            Claim(text="x", kind="fact", citations=[]),
            cite("nowhere#L1-2", good),
            cite(chunk.id, "words that are not there at all"),
        ],
    )
    assert sorted(failed_claims(draft, evidence)) == [2, 3, 4]
