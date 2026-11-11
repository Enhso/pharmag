import re
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from pharmag.corpus import MAX_CHARS, load_corpus

CORPUS = Path(__file__).parent.parent / "corpus"
HEADING = re.compile(r"(#{2,6}) (.*)")

# Top-level headings the section table deliberately leaves unmapped.
UNMAPPED_ON_PURPOSE = {"Notice:", "Other names"}

# --- synthetic documents ---------------------------------------------------

words = st.text(alphabet="abc def|", min_size=1, max_size=40).filter(lambda s: s.strip())
long_line = st.integers(1, 3000).map(lambda n: "x" * n)
line = st.one_of(words, words, long_line, words.map(lambda s: "# " + s))
block = st.lists(line, min_size=1, max_size=5).map(lambda ls: ("block", ls))
heading = st.tuples(st.integers(2, 5), words).map(lambda t: ("heading", t))
blanks = st.sampled_from([[], [""], ["", ""], ["  "]])
items = st.lists(st.tuples(st.one_of(block, block, heading), blanks), max_size=12)


@st.composite
def documents(draw):
    lines = ["# Title", ""]
    if draw(st.booleans()):
        lines.append("Source: http://example.org")
    for (kind, value), gap in draw(items):
        lines += [f"{'#' * value[0]} {value[1]}"] if kind == "heading" else value
        lines += gap
    return lines


def parse(lines, name="dailymed-testdrug.md"):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / name).write_bytes("\n".join(lines).encode())
        return load_corpus(Path(d))


def reference(lines):
    """For each body line number: its heading path. Written apart from the parser."""
    stack, owner = [], {}
    for n, text in enumerate(lines, start=1):
        m = HEADING.fullmatch(text)
        if n == 1 or text.startswith("Source: ") and n <= 3:
            continue
        if m:
            stack = [h for h in stack if h[0] < len(m[1])] + [(len(m[1]), m[2].strip())]
        elif text.strip():
            owner[n] = tuple(h[1] for h in stack)
    return owner


@given(documents())
def test_every_body_line_is_in_exactly_one_chunk(lines):
    chunks = parse(lines)
    for n in reference(lines):
        assert sum(c.line_start <= n <= c.line_end for c in chunks) == 1


@given(documents())
def test_text_is_the_files_lines_verbatim(lines):
    for c in parse(lines):
        assert c.text == "\n".join(lines[c.line_start - 1 : c.line_end])
        assert c.id == f"{c.file}#L{c.line_start}-{c.line_end}"


@given(documents())
def test_chunks_are_ordered_disjoint_and_uniquely_named(lines):
    chunks = parse(lines)
    for a, b in zip(chunks, chunks[1:]):
        assert a.line_end < b.line_start
    assert len({c.id for c in chunks}) == len(chunks)


@given(documents())
def test_chunks_respect_the_size_cap_unless_one_line(lines):
    for c in parse(lines):
        assert len(c.text) <= MAX_CHARS or c.line_start == c.line_end


@given(documents())
def test_no_chunk_contains_a_heading_or_blank_edge(lines):
    for c in parse(lines):
        assert not any(HEADING.fullmatch(t) for t in c.text.split("\n"))
        first, *_, last = c.text.split("\n") if "\n" in c.text else [c.text, c.text]
        assert first.strip() and last.strip()


@given(documents())
def test_heading_path_is_the_heading_stack(lines):
    owner = reference(lines)
    for c in parse(lines):
        for n in range(c.line_start, c.line_end + 1):
            if n in owner:
                assert c.heading_path == owner[n]


@given(documents())
def test_parsing_twice_gives_the_same_chunks(lines):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "dailymed-testdrug.md").write_bytes("\n".join(lines).encode())
        assert load_corpus(Path(d)) == load_corpus(Path(d))


def test_unknown_file_name_is_rejected_by_name(tmp_path):
    (tmp_path / "notes.md").write_text("# x\n")
    with pytest.raises(ValueError, match="notes.md"):
        load_corpus(tmp_path)


# --- the real corpus -------------------------------------------------------


@pytest.fixture(scope="module")
def chunks():
    return load_corpus(CORPUS)


def of(chunks, file, section=None):
    return [c for c in chunks if c.file == file and (section is None or c.section == section)]


def test_all_21_files_load(chunks):
    assert len({c.file for c in chunks}) == 21


def test_warfarin_contraindications(chunks):
    hits = [c for c in of(chunks, "dailymed-warfarin.md", "contraindications") if "Malignant hypertension" in c.text]
    assert hits and hits[0].line_start > 127 and hits[0].drug == "warfarin"


def test_apixaban_contraindications_carry_the_drug_name(chunks):
    hits = of(chunks, "dailymed-apixaban.md", "contraindications")
    assert hits and all(c.drug == "apixaban" for c in hits)
    assert any("ELIQUIS" in c.text for c in hits)


def test_atorvastatin_line_223_is_body_text(chunks):
    covering = [c for c in of(chunks, "dailymed-atorvastatin.md") if c.line_start <= 223 <= c.line_end]
    assert len(covering) == 1
    assert "See Section 7 for clinical significance" in covering[0].text
    assert not any(h.startswith("See Section 7") for c in chunks for h in c.heading_path)


def test_ibuprofen_preamble_is_the_boxed_warning(chunks):
    pre = [c for c in of(chunks, "dailymed-ibuprofen.md") if c.heading_path == ()]
    assert len(pre) == 1 and pre[0].section == "boxed_warning"
    assert "Cardiovascular Thrombotic Events" in pre[0].text


def test_no_table_block_is_split(chunks):
    for path in CORPUS.glob("*.md"):
        lines = path.read_text().split("\n")
        mine = of(chunks, path.name)
        n = 0
        while n < len(lines):
            if not lines[n].strip():
                n += 1
                continue
            m = n
            while m + 1 < len(lines) and lines[m + 1].strip():
                m += 1
            if any(" | " in t for t in lines[n : m + 1]) and not HEADING.fullmatch(lines[n]):
                body = [c for c in mine if c.line_start <= m + 1 and c.line_end >= n + 1]
                assert len(body) == 1, f"{path.name} lines {n + 1}-{m + 1}"
            n = m + 1


def test_section_presence(chunks):
    assert not of(chunks, "dailymed-aspirin.md", "contraindications")
    assert of(chunks, "dailymed-metformin.md", "contraindications")
    assert of(chunks, "medlineplus-warfarin.md", "brand_names")


def test_every_top_level_heading_is_mapped_or_listed(chunks):
    unmapped = {c.heading_path[0] for c in chunks if c.heading_path and c.section is None}
    assert unmapped <= UNMAPPED_ON_PURPOSE
