import asyncio
import logging
import time
from collections.abc import Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

from openai import AsyncOpenAI
from pydantic_ai import UsageLimits

from pharmag.agents import RoleModels, WorkerDeps, build_models, critic, planner, worker, writer
from pharmag.config import Settings
from pharmag.corpus import load_corpus
from pharmag.grounding import dangling_markers, drop_dangling, failed_claims, markers
from pharmag.index import Index, OpenAIEmbedder
from pharmag.models import (
    AskResponse,
    Caution,
    Chunk,
    ClaimVerdict,
    CriticReport,
    Draft,
    Findings,
    RemovedClaim,
    RoleUsage,
    SourceCitation,
    Stage,
    ToolCall,
    TraceEvent,
    Usage,
)
from pharmag.tools import Tools, _section_path

DISCLAIMER = (
    "This is general information from a small set of documents, not medical advice. "
    "Ask a doctor or pharmacist about your own treatment."
)
# Starting limits (DEC-026). The eval's measured latency and cost decide the final numbers.
MAX_WORKERS = 6
MAX_TOOL_CALLS = 10
MAX_RETRY_ROUNDS = 1

# Hard backstop on a worker's model requests: the tool budget, the final answer, and output retries.
WORKER_REQUEST_LIMIT = MAX_TOOL_CALLS + 5
CACHE_DROP_WARNING = 0.25

log = logging.getLogger("pharmag.pipeline")

Emit = Callable[[TraceEvent], None]


@dataclass(frozen=True)
class Engine:
    """Everything a request needs, built once at startup."""

    tools: Tools
    chunks: Mapping[str, Chunk]  # by chunk ID
    models: RoleModels
    cache_rates: dict[str, float] = field(default_factory=dict)  # last cache hit rate per role


class PipelineError(Exception):
    """A stage failed and no answer can be given. `stage` names where."""

    def __init__(self, stage: Stage, message: str) -> None:
        super().__init__(f"{stage}: {message}")
        self.stage = stage


async def build_engine(settings: Settings, corpus_dir: Path) -> Engine:
    """Parse the corpus, embed every chunk through the API, and build the role models."""
    chunks = load_corpus(corpus_dir)
    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    index = await Index.build(chunks, OpenAIEmbedder(client, settings.embedding_model))
    return Engine(Tools(chunks, index), {c.id: c for c in chunks}, build_models(settings))


@dataclass
class _Request:
    """The mutable state the stages of one question share."""

    engine: Engine
    emit: Emit | None
    started: float = field(default_factory=time.perf_counter)
    evidence: dict[str, Chunk] = field(default_factory=dict)  # only passages a tool returned in this request
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: dict[str, RoleUsage] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)

    def event(self, stage: Stage, kind: str, **data) -> None:
        if self.emit:
            self.emit(TraceEvent(stage=stage, kind=kind, data=data, elapsed=time.perf_counter() - self.started))

    @asynccontextmanager
    async def stage(self, name: Stage):
        self.event(name, "started")
        began = time.perf_counter()
        try:
            yield
        except PipelineError:
            raise
        except Exception as e:
            raise PipelineError(name, f"{type(e).__name__}: {e}") from e
        self.timings[name] = self.timings.get(name, 0.0) + time.perf_counter() - began
        self.event(name, "finished")

    async def run(self, role: str, agent, prompt: str, **kwargs):
        result = await agent.run(prompt, model=getattr(self.engine.models, role), **kwargs)
        self._record(role, result.usage)
        return result.output

    def _record(self, role: str, u) -> None:
        mine = self.usage.setdefault(role, RoleUsage())
        mine.requests += u.requests
        mine.input_tokens += u.input_tokens
        mine.cached_input_tokens += u.cache_read_tokens
        mine.output_tokens += u.output_tokens
        rate = u.cache_read_tokens / u.input_tokens if u.input_tokens else None
        log.info(
            "role=%s requests=%d input=%d cached=%d output=%d hit_rate=%s",
            role,
            u.requests,
            u.input_tokens,
            u.cache_read_tokens,
            u.output_tokens,
            "n/a" if rate is None else f"{rate:.2f}",
        )
        if rate is None:
            return
        before = self.engine.cache_rates.get(role)
        if before is not None and before - rate > CACHE_DROP_WARNING:
            log.warning("cache hit rate for %s fell from %.2f to %.2f", role, before, rate)
        self.engine.cache_rates[role] = rate

    def totals(self) -> tuple[dict[str, float], Usage]:
        total = RoleUsage()
        for u in self.usage.values():
            total.requests += u.requests
            total.input_tokens += u.input_tokens
            total.cached_input_tokens += u.cached_input_tokens
            total.output_tokens += u.output_tokens
        timings = {**self.timings, "total": time.perf_counter() - self.started}
        return timings, Usage(**total.model_dump(), by_role=dict(self.usage))


async def _research(req: _Request, stage: Stage, tasks: list[tuple[str, str]]) -> list[tuple[str, Findings]]:
    """One worker per (label, prompt), at most MAX_WORKERS at once. A failed worker reports itself in not_found."""
    gate = asyncio.Semaphore(MAX_WORKERS)

    async def one(label: str, prompt: str) -> Findings:
        async with gate:
            deps = WorkerDeps(
                tools=req.engine.tools,
                chunks=req.engine.chunks,
                evidence=req.evidence,
                tool_calls=req.tool_calls,
                on_call=lambda c: req.event(stage, "tool_call", **c.model_dump()),
                label=label,
                calls_left=MAX_TOOL_CALLS,
            )
            try:
                limits = UsageLimits(request_limit=WORKER_REQUEST_LIMIT)
                return await req.run("worker", worker, prompt, deps=deps, usage_limits=limits)
            except Exception as e:  # one failed worker must not fail the request
                return Findings(findings=[], not_found=f"The research failed: {type(e).__name__}: {e}")

    results = await asyncio.gather(*(one(label, prompt) for label, prompt in tasks))
    return [(label, r) for (label, _), r in zip(tasks, results)]


def _findings_text(pairs: list[tuple[str, Findings]]) -> str:
    blocks = []
    for label, r in pairs:
        lines = [f"Sub-question: {label}"]
        lines += [f"- {f.statement}\n  chunk_id: {f.chunk_id}\n  quote: {f.quote}" for f in r.findings]
        lines.append(f"Not found: {r.not_found or '(nothing missing)'}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _claims_text(draft: Draft) -> str:
    return "\n".join(
        f"[{n}] ({c.kind}) {c.text}" + "".join(f"\n    cites {x.chunk_id}: {x.quote}" for x in c.citations)
        for n, c in enumerate(draft.claims, 1)
    )


def _unsupported(verdicts: list[ClaimVerdict]) -> list[ClaimVerdict]:
    return [v for v in verdicts if v.status == "unsupported"]


async def _check(req: _Request, draft: Draft) -> tuple[list[ClaimVerdict], list[str]]:
    """Stages 4 and 5: the quote check, then the critic. Returns one verdict per claim and the unmarked statements."""
    async with req.stage("quote_check"):
        failed = failed_claims(draft, req.evidence)
    async with req.stage("review"):
        cited = dict.fromkeys(c.chunk_id for claim in draft.claims for c in claim.citations)
        passages = "\n\n".join(f"--- {cid}\n{req.evidence[cid].text}" for cid in cited if cid in req.evidence)
        review = await req.run(
            "critic",
            critic,
            f"Answer text:\n{draft.answer}\n\nClaims:\n{_claims_text(draft)}\n\nCited passages:\n{passages}",
        )
    given: dict[int, ClaimVerdict] = {}
    for v in review.verdicts:
        given.setdefault(v.claim, v)
    verdicts = []
    for n, claim in enumerate(draft.claims, 1):
        if n in failed:
            verdicts.append(ClaimVerdict(claim=n, status="unsupported", reason=failed[n], follow_up=claim.text))
        elif n in given:
            verdicts.append(given[n].model_copy(update={"follow_up": given[n].follow_up or claim.text}))
        else:
            verdicts.append(
                ClaimVerdict(claim=n, status="unsupported", reason="The critic gave no verdict.", follow_up=claim.text)
            )
    return verdicts, review.unmarked


def _answer_text(prose: str, cautions: list[Caution], source_lines: list[str]) -> str:
    parts = [prose]
    if cautions:
        parts.append("Cautions:\n" + "\n".join(f"[{c.marker}] {c.reason}" for c in cautions))
    if source_lines:
        parts.append("Sources:\n" + "\n".join(source_lines))
    return "\n\n".join([*parts, DISCLAIMER])


async def answer(question: str, engine: Engine, emit: Emit | None = None) -> AskResponse:
    """Run stages 1 to 8 of docs/architecture.md for one question. Raises PipelineError."""
    req = _Request(engine, emit)

    async with req.stage("plan"):
        plan = await req.run("planner", planner, question, deps=engine.tools)
    if not plan.in_scope:
        timings, usage = req.totals()
        refusal = f"I can only answer questions about the pharmacology of the medicines in my documents. {plan.reason}"
        none = CriticReport(review_rounds=0, verdicts=[], removed=[], cautions=[], unmarked=[], marker_check="passed")
        return AskResponse(
            answer=_answer_text(refusal, [], []),
            sources=[],
            citations=[],
            plan=plan,
            tool_calls=[],
            critic=none,
            disclaimer=DISCLAIMER,
            timings=timings,
            usage=usage,
        )

    async with req.stage("research"):
        tasks = [(sq.text, f"{sq.text}\nDrugs concerned: {', '.join(sq.drugs)}") for sq in plan.sub_questions]
        pairs = await _research(req, "research", tasks)
    async with req.stage("write"):
        draft = await req.run("writer", writer, f"Question: {question}\n\nFindings:\n{_findings_text(pairs)}")
    verdicts, unmarked = await _check(req, draft)
    rounds = 1

    for _ in range(MAX_RETRY_ROUNDS):
        queries = list(dict.fromkeys([v.follow_up or "" for v in _unsupported(verdicts)] + unmarked))
        if not queries:
            break
        async with req.stage("retry"):
            pairs += await _research(req, "retry", [(q, q) for q in queries[:MAX_WORKERS]])
            problems = "\n".join(f"[{v.claim}] {v.status}: {v.reason}" for v in verdicts)
            draft = await req.run(
                "writer",
                writer,
                f"Question: {question}\n\nFindings, old and new:\n{_findings_text(pairs)}\n\n"
                f"Previous draft:\n{draft.answer}\n{_claims_text(draft)}\n\nVerdicts on its claims:\n{problems}\n\n"
                "Statements with no marker:\n" + "\n".join(f"- {u}" for u in unmarked) + "\n\n"
                "Write a revised draft. Support each unsupported claim with the findings, or leave it out when the "
                "findings do not support it. Give every factual sentence a marker.",
            )
        verdicts, unmarked = await _check(req, draft)
        rounds += 1

    prose = draft.answer
    if _unsupported(verdicts) or unmarked:
        async with req.stage("redact"):
            removed = "\n".join(f"[{v.claim}] {draft.claims[v.claim - 1].text}" for v in _unsupported(verdicts))
            prose = await req.run(
                "writer",
                writer,
                "Rewrite this answer without the claims and statements listed below. Keep every other sentence, "
                "and keep each marker's number as it is; do not renumber. Return only the prose.\n\n"
                f"Answer:\n{draft.answer}\n\nClaims to remove:\n{removed or '(none)'}\n\n"
                "Statements to remove:\n" + "\n".join(f"- {u}" for u in unmarked),
                output_type=str,
            )

    async with req.stage("respond"):
        by_claim = {v.claim: v for v in verdicts}
        surviving = {n for n, v in by_claim.items() if v.status != "unsupported"}
        marker_check = "passed"
        if dangling_markers(prose, surviving):
            prose, marker_check = drop_dangling(prose, surviving), "repaired"
        cited = [n for n in dict.fromkeys(markers(prose)) if n in surviving]
        citations = [
            SourceCitation(
                marker=n,
                claim=draft.claims[n - 1].text,
                kind=draft.claims[n - 1].kind,
                status=by_claim[n].status,
                file=req.evidence[c.chunk_id].file,
                section=_section_path(req.evidence[c.chunk_id]),
                line_start=req.evidence[c.chunk_id].line_start,
                line_end=req.evidence[c.chunk_id].line_end,
                quote=c.quote,
            )
            for n in cited
            for c in draft.claims[n - 1].citations
        ]
        cautions = [
            Caution(marker=n, text=draft.claims[n - 1].text, reason=by_claim[n].reason)
            for n in cited
            if by_claim[n].status == "ambiguous"
        ]
        report = CriticReport(
            review_rounds=rounds,
            verdicts=verdicts,
            removed=[RemovedClaim(text=draft.claims[v.claim - 1].text, reason=v.reason) for v in _unsupported(verdicts)],
            cautions=cautions,
            unmarked=unmarked,
            marker_check=marker_check,
        )
        source_lines = [f"[{c.marker}] {c.file}, {c.section}, lines {c.line_start}-{c.line_end}" for c in citations]
    timings, usage = req.totals()
    return AskResponse(
        answer=_answer_text(prose, cautions, source_lines),
        sources=list(dict.fromkeys(c.file for c in citations)),
        citations=citations,
        plan=plan,
        tool_calls=req.tool_calls,
        critic=report,
        disclaimer=DISCLAIMER,
        timings=timings,
        usage=usage,
    )
