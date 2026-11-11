import asyncio
import itertools
from pathlib import Path

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from fakes import FakeEmbedder
from pharmag.corpus import load_corpus
from pharmag.index import Index
from pharmag.tools import Tools

CHUNKS = load_corpus(Path(__file__).parent.parent / "corpus")
TOOLS = Tools(CHUNKS, asyncio.run(Index.build(CHUNKS, FakeEmbedder())))
DRUGS = TOOLS.drugs
BRANDS = [(b, d) for d, names in TOOLS.brands.items() for b in names]
GLOSSARY_TERMS = [full for full, _ in TOOLS.glossary]

any_text = st.text(max_size=40)
flips = st.lists(st.booleans(), min_size=60, max_size=60)


def recase(text, flip):
    return "".join(c.upper() if f else c.lower() for c, f in zip(text, flip))


def search(*args, **kwargs):
    return asyncio.run(TOOLS.search_corpus(*args, **kwargs))


def names_all_drugs(note):
    return all(d in note for d in DRUGS)


def test_get_section_returns_exactly_the_matching_chunks_in_file_order():
    combos = {(c.drug, c.source, c.section) for c in CHUNKS if c.drug and c.section}
    assert combos
    for drug, source, section in combos:
        expected = [c.id for c in CHUNKS if (c.drug, c.source, c.section) == (drug, source, section)]
        result = TOOLS.get_section(drug, section, source)
        assert [p.chunk_id for p in result.passages] == expected


@given(st.sampled_from(DRUGS), st.sampled_from(DRUGS))
def test_every_interaction_passage_contains_a_term_it_reports(a, b):
    result = TOOLS.find_interactions(a, b)
    for p in result.passages:
        assert p.matched
        assert all(term.lower() in p.text.lower() for term in p.matched)


def test_interactions_are_the_same_in_both_argument_orders():
    for a, b in itertools.product(DRUGS, DRUGS):
        forward = {p.chunk_id for p in TOOLS.find_interactions(a, b).passages}
        backward = {p.chunk_id for p in TOOLS.find_interactions(b, a).passages}
        assert forward == backward


@settings(max_examples=200)
@given(any_text, any_text, any_text)
def test_no_tool_raises_and_an_unknown_drug_names_the_corpus_drugs(name, source, section):
    other = TOOLS.find_interactions(name, "warfarin")
    TOOLS.find_interactions(name, name)
    TOOLS.lookup_glossary(name)
    TOOLS.get_section("warfarin", section, source)
    search(name, source=source, section=section, k=-3)
    if TOOLS.resolve_drug(name) is None:
        assert TOOLS.get_section(name, section, source).passages == ()
        assert names_all_drugs(TOOLS.get_section(name, section, source).note)
        assert search("anything", drug=name).passages == ()
        assert names_all_drugs(search("anything", drug=name).note)
        assert "no document" in other.note


@given(any_text)
def test_unknown_source_or_section_in_search_gives_no_passages_and_lists_valid_ones(text):
    assume(text not in TOOLS.sources)
    result = search("dose", source=text)
    assert result.passages == () and all(s in result.note for s in TOOLS.sources)
    assume(text not in TOOLS.sections)
    result = search("dose", section=text)
    assert result.passages == () and all(s in result.note for s in TOOLS.sections)


@given(st.sampled_from(DRUGS), flips, st.text(" \t", max_size=3))
def test_resolve_drug_maps_each_generic_name_in_any_case(drug, flip, pad):
    assert TOOLS.resolve_drug(pad + recase(drug, flip) + pad) == drug


@given(st.sampled_from(BRANDS), flips, st.text(" \t", max_size=3))
def test_resolve_drug_maps_each_brand_name_in_any_case(brand_and_drug, flip, pad):
    brand, drug = brand_and_drug
    assert TOOLS.resolve_drug(pad + recase(brand, flip) + pad) == drug


@given(st.sampled_from(GLOSSARY_TERMS), flips)
def test_every_glossary_entry_is_found_by_its_own_term(term, flip):
    expected = dict(TOOLS.glossary)[term]
    assert expected in TOOLS.lookup_glossary(recase(term, flip)).passages


def test_get_section_examples():
    contra = TOOLS.get_section("warfarin", "contraindications")
    assert any("Malignant hypertension" in p.text for p in contra.passages)

    eliquis = TOOLS.get_section("Eliquis", "contraindications")
    assert {p.file for p in eliquis.passages} == {"dailymed-apixaban.md"}
    assert any("Active pathological bleeding" in p.text for p in eliquis.passages)

    aspirin = TOOLS.get_section("aspirin", "contraindications")
    assert aspirin.passages == () and "warnings" in aspirin.note


def test_warfarin_and_sertraline_find_each_other():
    result = TOOLS.find_interactions("warfarin", "sertraline")
    warfarin = [p for p in result.passages if p.file.endswith("warfarin.md")]
    sertraline = [p for p in result.passages if p.file.endswith("sertraline.md")]
    assert any("Serotonin Reuptake Inhibitors" in p.text for p in warfarin)
    assert any("international normalized ratio" in p.text.lower() for p in sertraline)


def test_warfarin_and_ibuprofen_find_the_warfarin_type_anticoagulants_passage():
    result = TOOLS.find_interactions("warfarin", "ibuprofen")
    assert any("Warfarin-type anticoagulants" in p.text and "synergistic" in p.text for p in result.passages)


def test_apixaban_and_ibuprofen_match_through_the_class_term():
    result = TOOLS.find_interactions("apixaban", "ibuprofen")
    class_only = [p for p in result.passages if p.file.endswith("apixaban.md") and p.matched == ("nsaid",)]
    assert any("NSAID" in p.text for p in class_only)


def test_a_drug_missing_from_the_corpus_is_named_in_the_note():
    result = TOOLS.find_interactions("warfarin", "rivaroxaban")
    assert "no document for 'rivaroxaban'" in result.note


def test_glossary_lookups():
    inr = TOOLS.lookup_glossary("INR")
    assert any("warfarin" in p.text for p in inr.passages)
    assert TOOLS.lookup_glossary("ssri").passages
    missing = TOOLS.lookup_glossary("zzz")
    assert missing.passages == () and "INR" in missing.note


def test_search_by_brand_name_returns_only_that_drug():
    result = search("depression dose", drug="Zoloft")
    assert result.passages
    assert {p.file for p in result.passages} <= {"dailymed-sertraline.md", "medlineplus-sertraline.md"}
    assert all(p.dense_rank is not None and p.score is not None for p in result.passages)
