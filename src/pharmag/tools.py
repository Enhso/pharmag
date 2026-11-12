import re
from dataclasses import dataclass

from pharmag.index import Index
from pharmag.models import Chunk

MAX_PER_DIRECTION = 8

_SUP = re.compile(r"<sup>.*?</sup>")
_CLASS_SENTENCE = re.compile(r"\bis in a (?:class|group) of [^.\n]*? called ([^\n]+?)\.(?=\s|$)")
_GLOSSARY_ENTRY = re.compile(r"- \*\*(.+?)\*\*:\s*(.*)")


@dataclass(frozen=True)
class Passage:
    chunk_id: str
    file: str
    section_path: str  # heading path joined with " > ", or "(preamble)"
    line_start: int
    line_end: int
    text: str
    score: float | None = None  # search_corpus only
    dense_rank: int | None = None
    bm25_rank: int | None = None
    matched: tuple[str, ...] = ()  # find_interactions only: the terms found in the text


@dataclass(frozen=True)
class ToolResult:
    passages: tuple[Passage, ...]
    note: str  # plain text for the model: explains an empty result, says what exists instead


def _section_path(chunk: Chunk) -> str:
    return " > ".join(chunk.heading_path) or "(preamble)"


def _passage(chunk: Chunk, **extra) -> Passage:
    return Passage(
        chunk.id, chunk.file, _section_path(chunk), chunk.line_start, chunk.line_end, chunk.text, **extra
    )


def _mention(term: str) -> re.Pattern[str]:
    """Whole-word, case-insensitive match; a trailing "s" is allowed so "NSAID" finds "NSAIDs"."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(term)}s?(?![a-z0-9])", re.IGNORECASE)


def _brand_names(chunk: Chunk) -> list[str]:
    names = []
    for line in chunk.text.splitlines():
        if line.startswith("- "):
            name = _SUP.sub("", line[2:])
            name = re.sub(r"\s*\(.*\)\s*$", "", name)  # "(as a combination product ...)"
            names.append(" ".join(name.split()))
    return [n for n in names if n]


def _class_terms(text: str) -> list[str]:
    terms: list[str] = []
    for phrase in _CLASS_SENTENCE.findall(text):
        pieces = re.findall(r"\(([^)]*)\)", phrase) + [re.sub(r"\([^)]*\)", "", phrase)]
        for piece in pieces:
            for part in piece.split(" and "):
                term = part.strip(" '\"").lower().removesuffix("s")
                if term and term not in terms:
                    terms.append(term)
    return terms


def _glossary_keys(full: str) -> set[str]:
    inside = re.search(r"\((.*)\)", full)
    keys = {full.lower(), full.split("(")[0].strip().lower()}
    return keys | {inside[1].strip().lower()} if inside else keys


class Tools:
    def __init__(self, chunks: list[Chunk], index: Index) -> None:
        self._chunks = chunks
        self._index = index
        self.drugs = sorted({c.drug for c in chunks if c.drug})
        self.sources = sorted({c.source for c in chunks})
        self.sections = sorted({c.section for c in chunks if c.section})
        self.brands: dict[str, list[str]] = {d: [] for d in self.drugs}
        for c in chunks:
            if c.source == "medlineplus" and c.heading_path[:1] == ("Brand names",) and c.drug:
                self.brands[c.drug] += _brand_names(c)
        self.classes: dict[str, list[str]] = {
            d: [t for c in chunks if c.drug == d for t in _class_terms(c.text)] for d in self.drugs
        }
        self._by_name = {d: d for d in self.drugs}
        for drug, names in self.brands.items():
            for name in names:
                self._by_name.setdefault(name.lower(), drug)
        self.glossary = self._parse_glossary()

    def resolve_drug(self, name: str) -> str | None:
        return self._by_name.get(name.strip().lower())

    def _unknown_drug(self, name: str) -> ToolResult:
        return ToolResult((), f"No drug named {name!r} in the corpus. Drugs: {', '.join(self.drugs)}.")

    async def search_corpus(
        self,
        query: str,
        drug: str | None = None,
        source: str | None = None,
        section: str | None = None,
        k: int = 6,
    ) -> ToolResult:
        generic = None
        if drug is not None:
            generic = self.resolve_drug(drug)
            if generic is None:
                return self._unknown_drug(drug)
        if source is not None and source not in self.sources:
            return ToolResult((), f"Unknown source {source!r}. Sources: {', '.join(self.sources)}.")
        if section is not None and section not in self.sections:
            return ToolResult((), f"Unknown section {section!r}. Sections: {', '.join(self.sections)}.")
        hits = await self._index.search(query, k=max(k, 1), drug=generic, source=source, section=section)
        passages = tuple(
            _passage(h.chunk, score=h.score, dense_rank=h.dense_rank, bm25_rank=h.bm25_rank) for h in hits
        )
        return ToolResult(passages, "" if passages else "No passage matches those filters.")

    def get_section(self, drug: str, section: str, source: str = "dailymed") -> ToolResult:
        generic = self.resolve_drug(drug)
        if generic is None:
            return self._unknown_drug(drug)
        of_drug = [c for c in self._chunks if c.drug == generic and c.source == source]
        if not of_drug:
            return ToolResult((), f"No {source!r} file for {generic}. Sources: {', '.join(self.sources)}.")
        found = [c for c in of_drug if c.section == section]
        if found:
            return ToolResult(tuple(_passage(c) for c in found), "")
        have = sorted({c.section for c in of_drug if c.section})
        return ToolResult(
            (), f"The {source} file for {generic} has no section {section!r}. Sections it has: {', '.join(have)}."
        )

    def find_interactions(self, drug_a: str, drug_b: str) -> ToolResult:
        a, b = self.resolve_drug(drug_a), self.resolve_drug(drug_b)
        passages: list[Passage] = []
        notes: list[str] = []
        for name, generic, other_name, other in ((drug_a, a, drug_b, b), (drug_b, b, drug_a, a)):
            if generic is None:
                notes.append(f"The corpus has no document for {name!r}.")
                continue
            found, more = self._mentions(generic, other, other_name)
            passages += found
            notes.append(
                f"{len(found)} passage(s) in the {generic} files mention {other or other_name!r}"
                + (f" ({more} more not shown)." if more else ".")
            )
        return ToolResult(tuple(passages), " ".join(notes))

    def _mentions(self, generic: str, other: str | None, other_name: str) -> tuple[list[Passage], int]:
        """Passages of `generic`'s files that mention `other`; `other` is None when it is not in the corpus."""
        if other is None:
            names, classes = [other_name.strip()], []
        else:
            names, classes = [other, *self.brands[other]], self.classes[other]
        patterns = [(t, _mention(t), True) for t in names if t] + [(t, _mention(t), False) for t in classes]
        ranked = []
        for chunk in self._chunks:
            if chunk.drug != generic:
                continue
            hits = [(t, by_name) for t, p, by_name in patterns if p.search(chunk.text)]
            if hits:
                ranked.append((not any(by_name for _, by_name in hits), chunk, tuple(t for t, _ in hits)))
        ranked.sort(key=lambda r: r[0])  # stable: file order within each group
        shown = ranked[:MAX_PER_DIRECTION]
        return [_passage(c, matched=m) for _, c, m in shown], len(ranked) - len(shown)

    def _parse_glossary(self) -> list[tuple[str, Passage]]:
        entries: list[tuple[str, Passage]] = []
        for chunk in self._chunks:
            if chunk.source != "glossary":
                continue
            lines = [line.rstrip() for line in chunk.text.split("\n")]  # the file has CRLF line ends
            starts = [i for i, line in enumerate(lines) if _GLOSSARY_ENTRY.match(line)]
            for n, start in enumerate(starts):
                body = lines[start : starts[n + 1] if n + 1 < len(starts) else len(lines)]
                while not body[-1]:
                    body.pop()
                term = _GLOSSARY_ENTRY.match(lines[start])[1]
                first = chunk.line_start + start
                entries.append(
                    (
                        term,
                        Passage(
                            chunk.id, chunk.file, _section_path(chunk), first, first + len(body) - 1, "\n".join(body)
                        ),
                    )
                )
        return entries

    def lookup_glossary(self, term: str) -> ToolResult:
        wanted = term.strip().lower()
        found = [p for full, p in self.glossary if wanted and wanted in _glossary_keys(full)]
        # shortcut: substring match reads the term only, not the definition; upgrade if the model asks by description
        found = found or [p for full, p in self.glossary if wanted and wanted in full.lower()]
        if found:
            return ToolResult(tuple(found), "")
        terms = ", ".join(full for full, _ in self.glossary)
        return ToolResult((), f"No glossary entry for {term!r}. Terms: {terms}.")
