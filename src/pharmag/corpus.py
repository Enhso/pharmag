import re
from pathlib import Path

from pharmag.models import Chunk

MAX_CHARS = 5000

_HEADING = re.compile(r"(#{2,6}) (.*)")
_FILE_NAME = re.compile(r"(dailymed|medlineplus)-(.+)")
_NUMBERED_HEADING = re.compile(r"(\d+)(\.\d+)* ")

_NUMBERED = {
    1: "indications",
    2: "dosage",
    4: "contraindications",
    5: "warnings",
    6: "adverse_reactions",
    7: "interactions",
    8: "specific_populations",
    10: "overdosage",
    12: "pharmacology",
    17: "patient_counseling",
}

# Matched against the lowercased top-level heading, by its start.
_BY_PREFIX = [
    ("indications and usage", "indications"),
    ("uses", "indications"),
    ("dosage and administration", "dosage"),
    ("directions", "dosage"),
    ("contraindications", "contraindications"),
    ("warnings", "warnings"),
    ("adverse reactions", "adverse_reactions"),
    ("drug interactions", "interactions"),
    ("pregnancy", "specific_populations"),
    ("labor and delivery", "specific_populations"),
    ("nursing mothers", "specific_populations"),
    ("pediatric use", "specific_populations"),
    ("geriatric use", "specific_populations"),
    ("overdosage", "overdosage"),
    ("in case of overdose", "overdosage"),
    ("clinical pharmacology", "pharmacology"),
    ("information for patients", "patient_counseling"),
    ("patient information", "patient_counseling"),
    ("why is this medication prescribed", "indications"),
    ("how should this medicine be used", "dosage"),
    ("other uses for this medicine", "other_uses"),
    ("what special precautions should i follow", "precautions"),
    ("what special dietary instructions", "diet"),
    ("what should i do if i forget a dose", "missed_dose"),
    ("what side effects can this medication cause", "adverse_reactions"),
    ("what should i know about storage and disposal", "storage"),
    ("in case of emergency/overdose", "overdosage"),
    ("what other information should i know", "other_information"),
    ("brand names", "brand_names"),
]


def load_corpus(directory: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(directory.iterdir()):
        if path.suffix in (".md", ".txt"):
            source, drug = _file_identity(path)
            lines = path.read_bytes().decode("utf-8").split("\n")
            chunks += _file_chunks(path.name, source, drug, lines)
    return chunks


def _file_identity(path: Path) -> tuple[str, str | None]:
    if path.stem == "GLOSSARY":
        return "glossary", None
    m = _FILE_NAME.fullmatch(path.stem)
    if m is None:
        raise ValueError(f"unrecognised corpus file name: {path.name}")
    return m[1], m[2]


def _file_chunks(file: str, source: str, drug: str | None, lines: list[str]) -> list[Chunk]:
    chunks = []
    for path, start, end in _sections(lines):
        body = [i for i in range(start, end) if lines[i].strip()]
        section = _canonical_section(source, path)
        for a, b in _pack(lines, _units(body, lines)):
            chunks.append(
                Chunk(
                    id=f"{file}#L{a + 1}-{b + 1}",
                    file=file,
                    drug=drug,
                    source=source,  # type: ignore[arg-type]
                    section=section,
                    heading_path=path,
                    line_start=a + 1,
                    line_end=b + 1,
                    text="\n".join(lines[a : b + 1]),
                )
            )
    return chunks


def _sections(lines: list[str]) -> list[tuple[tuple[str, ...], int, int]]:
    """(heading_path, first_line_index, end_index_exclusive) for the text under each heading."""
    sections = []
    stack: list[tuple[int, str]] = []
    path: tuple[str, ...] = ()
    start = 1  # index 0 is the title
    for i in range(1, len(lines)):
        m = _HEADING.fullmatch(lines[i])
        if m:
            sections.append((path, start, i))
            level = len(m[1])
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m[2].strip()))
            path = tuple(title for _, title in stack)
            start = i + 1
        elif i < 5 and not sections and lines[i].startswith("Source: "):
            start = i + 1
    sections.append((path, start, len(lines)))
    return sections


def _units(body: list[int], lines: list[str]) -> list[tuple[int, int]]:
    """Blocks (runs of consecutive non-blank lines) as (first, last) indexes.

    A block over the cap becomes one unit per line.
    """
    blocks: list[list[int]] = []
    for i in body:
        if blocks and blocks[-1][-1] == i - 1:
            blocks[-1].append(i)
        else:
            blocks.append([i])
    units = []
    for block in blocks:
        if len("\n".join(lines[block[0] : block[-1] + 1])) > MAX_CHARS:
            units += [(i, i) for i in block]
        else:
            units.append((block[0], block[-1]))
    return units


def _pack(lines: list[str], units: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Join neighbouring units while the joined lines stay within MAX_CHARS."""
    packed: list[tuple[int, int]] = []
    for a, b in units:
        if packed and len("\n".join(lines[packed[-1][0] : b + 1])) <= MAX_CHARS:
            packed[-1] = (packed[-1][0], b)
        else:
            packed.append((a, b))
    return packed


def _canonical_section(source: str, path: tuple[str, ...]) -> str | None:
    if source == "glossary":
        return "glossary"
    if not path:
        # shortcut: any text before the first heading counts as a boxed warning (true for DailyMed here), upgrade when a label's preamble is something else
        return "boxed_warning" if source == "dailymed" else None
    top = path[0].casefold()
    if top.startswith(("warning:", "important warning")):
        return "boxed_warning"
    number = _NUMBERED_HEADING.match(top)
    if number:
        return _NUMBERED.get(int(number[1]))
    return next((key for prefix, key in _BY_PREFIX if top.startswith(prefix)), None)
