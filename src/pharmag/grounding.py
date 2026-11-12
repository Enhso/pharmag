import re
import unicodedata
from collections.abc import Collection, Mapping

from pharmag.models import Chunk, Draft

_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_LEADING_MARKERS = re.compile(rf"{_MARKER.pattern}(?:\s*{_MARKER.pattern})*")
# A sentence ends after . ! ? plus whitespace when a new sentence starts there, and never right after an abbreviation.
_SENTENCE_BREAK = re.compile(
    r"((?<=[.!?])(?<!e\.g\.)(?<!i\.e\.)(?<!St\.)(?<!vs\.)(?<!Dr\.)\s+(?=[A-Z0-9\[(]|-\s)|\n+)"
)


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


def _sentences(prose: str) -> list[str]:
    """Split prose into sentences, each with the whitespace after it; joining them gives the prose back."""
    # shortcut: the abbreviation list is short and a sentence must start with a capital, digit, bullet, [ or (;
    # upgrade to a real sentence splitter if a redaction ever cuts the wrong span
    parts = _SENTENCE_BREAK.split(prose)  # sentence, break, sentence, break, ...
    for i in range(2, len(parts), 2):  # markers after the final punctuation belong to the sentence before
        if m := _LEADING_MARKERS.match(parts[i]):
            rest = parts[i][m.end() :]
            parts[i - 2] += parts[i - 1] + m[0]
            parts[i - 1], parts[i] = rest[: len(rest) - len(rest.lstrip())], rest.lstrip()
    return ["".join(parts[i : i + 2]) for i in range(0, len(parts), 2)]


def drop_dangling(prose: str, surviving: Collection[int]) -> str:
    """Remove each sentence that carries a dangling marker; every other sentence stays as it was."""
    return "".join(s for s in _sentences(prose) if not dangling_markers(s, surviving)).strip()


def sentences_with(prose: str, numbers: Collection[int]) -> list[str]:
    """The sentences of the prose that carry one of the markers."""
    return [s for s in _sentences(prose) if set(markers(s)) & set(numbers)]


def _plain(text: str) -> str:
    return normalize(re.sub(rf"\s*{_MARKER.pattern}", "", text))


def drop_sentences(prose: str, banned: Collection[str]) -> str:
    """Remove each sentence that contains one of the banned texts, compared without markers and through normalize."""
    # shortcut: this sees a banned sentence kept word for word, not a paraphrase of it; only a reviewer sees that
    wanted = [w for w in map(_plain, banned) if w]
    return "".join(s for s in _sentences(prose) if not any(w in _plain(s) for w in wanted)).strip()
