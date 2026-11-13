import unicodedata
from pathlib import Path

from hypothesis import assume, given
from hypothesis import strategies as st

from pharmag.corpus import load_corpus
from pharmag.grounding import (
    _TOKEN,
    dangling_markers,
    drop_dangling,
    drop_sentences,
    failed_claims,
    markers,
    normalize,
    quote_occurs,
    sentences_with,
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


@st.composite
def token_run_of_a_passage(draw):
    """A passage and a run of its whole tokens, written back with the given separators and a punctuated end."""
    passage = draw(st.sampled_from(PASSAGES))
    tokens = _TOKEN.findall(unicodedata.normalize("NFKC", passage).casefold())
    a = draw(st.integers(0, len(tokens) - 1))
    b = draw(st.integers(a + 1, len(tokens)))
    # every separator holds a space, so two numbers never fuse into one
    sep = st.text(alphabet=" \t\n.,;:()[]-*_\\\"'", min_size=1, max_size=4).map(lambda s: " " + s)
    seps = draw(st.lists(sep, min_size=b - a + 1, max_size=b - a + 1))
    quote = seps[0] + "".join(t + s for t, s in zip(tokens[a:b], seps[1:]))
    return passage, quote


@given(token_run_of_a_passage(), st.sampled_from(["keep", "upper", "lower"]))
def test_any_run_of_whole_tokens_passes_after_reflow_case_change_and_punctuation(drawn, case):
    passage, quote = drawn
    assert quote_occurs({"keep": quote, "upper": quote.upper(), "lower": quote.lower()}[case], passage)


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


# "vs" is left out: a sentence ending in "vs." does not end there, by design
sentence = st.tuples(st.lists(word.filter(lambda w: w != "vs"), min_size=1, max_size=5), st.lists(numbers, max_size=2))


@given(st.lists(sentence, max_size=8), st.sets(numbers, max_size=10))
def test_drop_dangling_leaves_no_dangling_marker_and_keeps_every_clean_sentence(sentences, surviving):
    # each sentence starts with its own token S<i>, so a dropped sentence's words are provably gone
    rendered = [" ".join([f"S{i}", *words]) + "".join(f" [{n}]" for n in nums) + "." for i, (words, nums) in enumerate(sentences)]
    result = drop_dangling(" ".join(rendered), surviving)
    assert dangling_markers(result, surviving) == []
    clean = [text for text, (_, nums) in zip(rendered, sentences) if all(n in surviving for n in nums)]
    assert result == " ".join(clean)


def test_markers_after_the_final_punctuation_go_with_their_sentence():
    prose = "A is true [1]. B is a rare but serious illness. [1][2] C is fine [1]."
    assert drop_dangling(prose, {1}) == "A is true [1]. C is fine [1]."
    assert drop_dangling("A [1]. B. [1] [3] C [1].", {1}) == "A [1]. C [1]."


def test_an_abbreviation_does_not_end_a_sentence():
    prose = "Avoid NSAIDs, e.g. ibuprofen [2]. Warfarin is an anticoagulant [1]."
    assert drop_dangling(prose, {1}) == "Warfarin is an anticoagulant [1]."
    assert drop_dangling("It is X, i.e. Warfarin [2]. Y [1]. See Dr. Who [2]. Z vs. Warfarin [2]. W [1].", {1}) == "Y [1]. W [1]."
    assert drop_dangling("A [2].\nB [1].\n- C [2]\n- D [1]", {1}) == "B [1].\n- D [1]"


def test_drop_sentences_removes_a_banned_sentence_kept_word_for_word_with_or_without_its_marker():
    prose = "Warfarin is an anticoagulant. Apixaban is **contraindicated** in moon dust allergy. Fine [1]."
    banned = ["Apixaban is contraindicated in moon dust allergy [2]."]
    assert drop_sentences(prose, banned) == "Warfarin is an anticoagulant. Fine [1]."
    assert drop_sentences(prose.replace("allergy.", "allergy [2]."), banned) == "Warfarin is an anticoagulant. Fine [1]."
    assert drop_sentences(prose, ["", " [3] "]) == prose  # a banned text with nothing in it removes nothing


def test_sentences_with_returns_the_sentences_that_carry_a_marker():
    assert sentences_with("A [1]. B [2][3]. C.", {3}) == ["B [2][3]. "]


def test_the_quote_check_ignores_markdown_emphasis_and_unicode_compatibility_forms():
    assert quote_occurs("the **ﬁrst** dose", "The first  dose is")  # ligature, emphasis, spacing
    assert quote_occurs("１０ mg", "take 10 mg daily")  # full-width digits


REAL_QUOTES = {  # worker quotes from live runs, checked against the real corpus chunks
    "dailymed-sertraline.md#L324-358": "For patients taking warfarin, carefully monitor the international normalized ratio.",
    "dailymed-warfarin.md#L231-235": "More frequent INR monitoring should be performed when starting or stopping other drugs, including botanicals, or when changing dosages of other drugs.",
    "medlineplus-ibuprofen.md#L7-15": "Tell your doctor if you take any of the following medications: anticoagulants ('blood thinners'); aspirin; other NSAIDs such as naproxen (Aleve, Naprosyn); oral steroids such as dexamethasone, methylprednisolone (Medrol), and prednisone (Rayos).",
    "medlineplus-warfarin.md#L7-19": "Keep all appointments with your doctor and the laboratory. Your doctor will order a blood test (PT [prothrombin test] reported as INR [international normalized ratio] value) regularly to check your body's response to warfarin.",
    "medlineplus-sertraline.md#L73-83": "Some side effects can be serious. If you experience any of the following symptoms or those listed in the IMPORTANT WARNING or SPECIAL PRECAUTIONS section, call your doctor immediately: - abnormal bleeding or bruising",
    "dailymed-ibuprofen.md#L302-315": "Instruct patients to seek medical advice if they observe any indicative signs or symptoms of GI ulcerations and bleeding, including epigastric pain, dyspepsia, melena, and hematemesis.",
}
BY_ID = {c.id: c.text for c in CHUNKS}


def test_real_quotes_that_differ_only_in_punctuation_pass_and_a_stitched_or_paraphrased_quote_fails():
    results = {cid: quote_occurs(q, BY_ID[cid]) for cid, q in REAL_QUOTES.items()}
    assert [cid for cid, ok in results.items() if ok] == list(REAL_QUOTES)[:4]
    assert not results["medlineplus-sertraline.md#L73-83"] and not results["dailymed-ibuprofen.md#L302-315"]


def test_the_quote_check_compares_whole_words_and_whole_numbers():
    assert not quote_occurs("5 mg", "take 0.5 mg daily")
    assert not quote_occurs("eGFR < 30", "eGFR ≥ 30 mL")
    assert not quote_occurs("the", "other drugs")
    assert quote_occurs("Malignant hypertension", "- Malignant hypertension\n- x")
    assert quote_occurs("0.5 mg", "take 0.5 mg daily") and quote_occurs("eGFR ≥ 30", "eGFR ≥ 30 mL")


def test_failed_claims_reads_every_citation_of_a_claim():
    chunk = CHUNKS[0]
    good = Citation(chunk_id=chunk.id, quote=" ".join(chunk.text.split()[:5]))
    bad = Citation(chunk_id=chunk.id, quote="words that are not there at all")
    draft = Draft(answer="", claims=[Claim(text="x", kind="synthesis", citations=[good, bad])])
    assert list(failed_claims(draft, {chunk.id: chunk})) == [1]


def test_a_citation_to_a_real_chunk_that_no_tool_returned_fails():
    chunk = CHUNKS[0]
    cited = Citation(chunk_id=chunk.id, quote=" ".join(chunk.text.split()[:5]))
    draft = Draft(answer="", claims=[Claim(text="x", kind="fact", citations=[cited])])
    assert failed_claims(draft, {}) != {} and failed_claims(draft, {chunk.id: chunk}) == {}


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
