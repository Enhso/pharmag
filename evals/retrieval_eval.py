"""Retrieval eval: heading-tree chunks against fixed-size windows over the same corpus.

Run from the repo root: uv run --env-file .env python evals/retrieval_eval.py
"""

import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple

from embedding_cache import CachingEmbedder
from openai import AsyncOpenAI

from pharmag.config import load_settings
from pharmag.corpus import load_corpus
from pharmag.index import Hit, Index, OpenAIEmbedder
from pharmag.models import Chunk

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
K = 6
WINDOW_SIZE = 1000
WINDOW_OVERLAP = 200
SETS = ("ours", "baseline")
MODES = ("question", "question+drug")

CAVEATS = [
    "The sample is 13 gold files from 9 questions, so one file is 7.7 points of recall.",
    "The query is the raw question, not an agent's sub-question.",
    "Our chunks reach 5,000 characters and the windows 1,000, and a hit needs only one line of "
    "overlap with the gold range, so a larger chunk is easier to hit.",
]


class Window(NamedTuple):
    start: int  # character offsets, end exclusive
    end: int
    line_start: int  # 1-based, inclusive
    line_end: int


class GoldFile(NamedTuple):
    id: str
    question: str
    file: str
    ranges: list[list[int]]


def fixed_windows(text: str, size: int, overlap: int) -> list[Window]:
    """Windows of at most `size` characters, each starting `size - overlap` after the one before."""
    if not 0 <= overlap < size:
        raise ValueError("overlap must be at least 0 and less than size")
    windows = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # a newline belongs to the line it ends
        line_start = 1 + text.count("\n", 0, start)
        line_end = 1 + text.count("\n", 0, end - 1)
        windows.append(Window(start, end, line_start, line_end))
        if end == len(text):
            break
        start += size - overlap
    return windows


def baseline_chunks(directory: Path, ours: list[Chunk]) -> list[Chunk]:
    """Fixed windows over each file's full text. Drug and source come from the parser's chunks."""
    parsed = {c.file: c for c in ours}
    chunks = []
    for file, p in parsed.items():
        text = (directory / file).read_bytes().decode("utf-8")  # as the parser reads it
        for w in fixed_windows(text, WINDOW_SIZE, WINDOW_OVERLAP):
            chunks.append(
                Chunk(
                    id=f"{file}#C{w.start}-{w.end}",  # line ranges repeat when a line is long
                    file=file,
                    drug=p.drug,
                    source=p.source,
                    section=None,
                    heading_path=(),
                    line_start=w.line_start,
                    line_end=w.line_end,
                    text=text[w.start : w.end],
                )
            )
    return chunks


def touches(chunk: Chunk, file: str, ranges: list[list[int]]) -> bool:
    return chunk.file == file and any(chunk.line_start <= hi and lo <= chunk.line_end for lo, hi in ranges)


def rank_of(hits: list[Hit], file: str, ranges: list[list[int]]) -> int | None:
    return next((r for r, h in enumerate(hits, 1) if touches(h.chunk, file, ranges)), None)


def check_gold(name: str, chunks: list[Chunk], gold: list[GoldFile]) -> None:
    """A gold range that no chunk covers can never be found, which would lower the score by construction."""
    for g in gold:
        for r in g.ranges:
            if not any(touches(c, g.file, [r]) for c in chunks):
                raise ValueError(f"{name}: no chunk covers {g.id} {g.file} lines {r[0]}-{r[1]}")


def metrics(ranks: list[int | None]) -> dict[str, float]:
    found = [r for r in ranks if r is not None]
    return {
        "recall@3": sum(r <= 3 for r in found) / len(ranks),
        f"recall@{K}": len(found) / len(ranks),
        "mrr": sum(1 / r for r in found) / len(ranks),
    }


async def rank_gold(index: Index, gold: list[GoldFile], drugs: dict[str, str | None]) -> dict[str, list[int | None]]:
    ranks: dict[str, list[int | None]] = {m: [] for m in MODES}
    for g in gold:
        plain = await index.search(g.question, k=K)
        ranks["question"].append(rank_of(plain, g.file, g.ranges))
        scoped = await index.search(g.question, k=K, drug=drugs[g.file])
        ranks["question+drug"].append(rank_of(scoped, g.file, g.ranges))
    return ranks


def render(gold: list[GoldFile], ranks: dict, scores: dict) -> str:
    head = ["id", "gold file"] + [f"{s}/{m}" for s in SETS for m in MODES]
    rows = [head]
    for i, g in enumerate(gold):
        cells = [ranks[s][m][i] for s in SETS for m in MODES]
        rows.append([g.id, g.file] + ["-" if r is None else str(r) for r in cells])
    rows.append([""] * len(head))
    for name in scores["ours"]["question"]:
        rows.append(["", name] + [f"{scores[s][m][name]:.3f}" for s in SETS for m in MODES])
    widths = [max(len(row[c]) for row in rows) for c in range(len(head))]
    lines = [
        "  ".join(cell.ljust(w) if c < 2 else cell.rjust(w) for c, (cell, w) in enumerate(zip(row, widths))).rstrip()
        for row in rows
    ]
    lines.insert(1, "-" * len(lines[0]))
    return "\n".join(lines)


async def main() -> None:
    settings = load_settings(os.environ)
    if isinstance(settings, list):
        sys.exit("\n".join(f"{p.variable} {p.problem}" for p in settings))
    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    embedder = CachingEmbedder(
        OpenAIEmbedder(client, settings.embedding_model),
        settings.embedding_model,
        ROOT / "evals" / ".cache",
    )

    questions = json.loads((ROOT / "evals" / "questions.json").read_text())["questions"]
    gold = [GoldFile(q["id"], q["question"], g["file"], g["lines"]) for q in questions for g in q["gold"]]
    ours = load_corpus(CORPUS)
    chunk_sets = {"ours": ours, "baseline": baseline_chunks(CORPUS, ours)}
    drugs = {c.file: c.drug for c in ours}
    assert len(gold) == 13, f"expected 13 gold files, found {len(gold)}"

    ranks = {}
    for name, chunks in chunk_sets.items():
        check_gold(name, chunks, gold)
        before = embedder.sent
        index = await Index.build(chunks, embedder)
        print(f"{name}: {len(chunks)} chunks, {embedder.sent - before} texts sent to the embedding model")
        before = embedder.sent
        ranks[name] = await rank_gold(index, gold, drugs)
        print(f"{name}: {embedder.sent - before} queries sent to the embedding model")
    scores = {s: {m: metrics(ranks[s][m]) for m in MODES} for s in SETS}

    print()
    print(render(gold, ranks, scores))

    result = {
        "date": datetime.date.today().isoformat(),
        "embedding_model": settings.embedding_model,
        "k": K,
        "window_size": WINDOW_SIZE,
        "window_overlap": WINDOW_OVERLAP,
        "chunk_counts": {s: len(chunk_sets[s]) for s in SETS},
        "gold_files": [
            {"id": g.id, "file": g.file, "ranks": {s: {m: ranks[s][m][i] for m in MODES} for s in SETS}}
            for i, g in enumerate(gold)
        ],
        "metrics": scores,
        "caveats": CAVEATS,
    }
    out = ROOT / "evals" / "results" / "retrieval.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
