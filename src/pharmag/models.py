from dataclasses import dataclass
from typing import Literal

Source = Literal["dailymed", "medlineplus", "glossary"]


@dataclass(frozen=True)
class Chunk:
    """One passage of one corpus file, cut on the file's heading tree."""

    id: str  # "<file>#L<line_start>-<line_end>"
    file: str
    drug: str | None  # None for the glossary
    source: Source
    section: str | None  # canonical key such as "contraindications"; None when no key fits
    heading_path: tuple[str, ...]  # headings from the top level down to this passage
    line_start: int  # 1-based, inclusive
    line_end: int  # 1-based, inclusive
    text: str  # the file's lines line_start..line_end, verbatim, so a quote can be checked
