import re
import unicodedata
from collections.abc import Collection, Mapping

from pharmag.models import Chunk, Draft

_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_SENTENCE_BREAK = re.compile(r"((?<=[.!?])\s+|\n+)")


def normalize(text: str) -> str:
    """Fold a text so that a quote compares equal to the passage despite spacing, case and Markdown emphasis."""
    return " ".join(unicodedata.normalize("NFKC", text).replace("*", "").split()).casefold()


def quote_occurs(quote: str, passage: str) -> bool:
    wanted = normalize(quote)
    return bool(wanted) and wanted in normalize(passage)


def failed_claims(draft: Draft, evidence: Mapping[str, Chunk]) -> dict[int, str]:
    """Marker number to the reason its first bad citation fails; claims that pass are absent."""
    failed: dict[int, str] = {}
    for n, claim in enumerate(draft.claims, 1):
        if not claim.citations:
            failed[n] = "The claim cites no passage."
            continue
        for c in claim.citations:
            chunk = evidence.get(c.chunk_id)
            if chunk is None:
                failed[n] = f"The claim cites {c.chunk_id}, which no tool returned during this request."
            elif not quote_occurs(c.quote, chunk.text):
                failed[n] = f"The quote does not occur in {c.chunk_id}."
            else:
                continue
            break
    return failed


def markers(prose: str) -> list[int]:
    return [int(n) for m in _MARKER.finditer(prose) for n in re.findall(r"\d+", m[1])]


def dangling_markers(prose: str, surviving: Collection[int]) -> list[int]:
    return [n for n in markers(prose) if n not in surviving]


def drop_dangling(prose: str, surviving: Collection[int]) -> str:
    """Remove each sentence that carries a dangling marker; every other sentence stays as it was."""
    # shortcut: a sentence ends at . ! ? plus whitespace, or at a line break, so "e.g. " ends one early;
    # upgrade to a real sentence splitter if a redaction ever cuts the wrong span
    parts = _SENTENCE_BREAK.split(prose)  # sentence, break, sentence, break, ...
    kept = [
        "".join(parts[i : i + 2]) for i in range(0, len(parts), 2) if not dangling_markers(parts[i], surviving)
    ]
    return "".join(kept).strip()
