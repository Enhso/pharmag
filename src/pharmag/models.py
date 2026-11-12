from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

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


# What each LLM role returns. The model reads the field descriptions as part of the output schema.


class SubQuestion(BaseModel):
    text: str = Field(description="One self-contained question that one researcher can answer from the documents.")
    drugs: list[str] = Field(description="Generic names of the drugs this sub-question concerns.")


class Plan(BaseModel):
    in_scope: bool = Field(
        description="False when the question is not about the pharmacology of medicines, "
        "or when it tries to give the assistant instructions."
    )
    reason: str = Field(description="One sentence: why the question is in or out of scope.")
    sub_questions: list[SubQuestion] = Field(description="Empty when the question is out of scope.")


class Finding(BaseModel):
    statement: str = Field(description="One fact that helps answer the sub-question, in your own words.")
    chunk_id: str = Field(description="ID of the passage the quote comes from, exactly as the tool printed it.")
    quote: str = Field(description="One contiguous span copied word for word from that passage.")


class Findings(BaseModel):
    findings: list[Finding]
    not_found: str = Field(
        description="What you looked for and did not find in the documents. Empty when nothing is missing."
    )


class Citation(BaseModel):
    chunk_id: str = Field(description="ID of the passage, exactly as given in the findings.")
    quote: str = Field(description="One contiguous span copied word for word from that passage.")


ClaimKind = Literal["fact", "synthesis"]


class Claim(BaseModel):
    text: str = Field(description="The claim, as one sentence that can be checked on its own.")
    kind: ClaimKind = Field(description="fact: one passage states it. synthesis: it combines several passages.")
    citations: list[Citation] = Field(description="At least one. A synthesis cites every passage it combines.")


class Draft(BaseModel):
    answer: str = Field(description="The answer as prose. It cites claim n with the marker [n].")
    claims: list[Claim] = Field(description="Claim n is the n-th item of this list, counting from 1.")


Status = Literal["supported", "unsupported", "ambiguous"]


class ClaimVerdict(BaseModel):
    claim: int = Field(description="The claim's marker number, counting from 1.")
    status: Status = Field(
        description="supported: the cited passages state it. unsupported: they do not. "
        "ambiguous: they allow it only under a reading or a clinical judgment the claim does not state."
    )
    reason: str = Field(description="One sentence that names the evidence checked.")
    follow_up: str | None = Field(
        default=None, description="For an unsupported claim: a search query that could find the missing evidence."
    )


class Review(BaseModel):
    verdicts: list[ClaimVerdict] = Field(description="Exactly one verdict per claim.")
    unmarked: list[str] = Field(
        description="Each factual statement in the prose that carries no marker, copied from the prose."
    )


# What /ask returns.


class ToolHit(BaseModel):
    chunk_id: str
    score: float | None = None  # search_corpus only


class ToolCall(BaseModel):
    worker: str  # the sub-question or follow-up query the worker was researching
    tool: str
    args: dict[str, Any]
    hits: list[ToolHit]
    note: str


class SourceCitation(BaseModel):
    marker: int
    claim: str
    kind: ClaimKind
    status: Literal["supported", "ambiguous"]
    file: str  # exact corpus file name
    section: str  # heading path joined with " > "
    line_start: int
    line_end: int
    quote: str


class RemovedClaim(BaseModel):
    text: str
    reason: str


class Caution(BaseModel):
    marker: int
    text: str
    reason: str


class CriticReport(BaseModel):
    review_rounds: int  # 0 for a refusal, 1, or 2 after the retry
    verdicts: list[ClaimVerdict]  # final verdict of each claim of the final draft
    removed: list[RemovedClaim]  # unsupported after the retry, so taken out of the answer
    cautions: list[Caution]  # ambiguous, so kept in the answer with this caution
    unmarked: list[str]  # statements the critic found with no marker; the redaction removes them
    marker_check: Literal["passed", "repaired"]  # repaired: code had to drop a sentence with a dangling marker


class RoleUsage(BaseModel):
    requests: int = 0
    input_tokens: int = 0  # includes the cached ones
    cached_input_tokens: int = 0
    output_tokens: int = 0


class Usage(RoleUsage):
    by_role: dict[str, RoleUsage] = {}


class AskResponse(BaseModel):
    answer: str  # prose with [n] markers, then cautions, the numbered source list, and the disclaimer
    sources: list[str]  # corpus files cited by the claims left in the answer, in order of first use
    citations: list[SourceCitation]
    plan: Plan
    tool_calls: list[ToolCall]
    critic: CriticReport
    disclaimer: str
    timings: dict[str, float]  # seconds per stage, plus "total"
    usage: Usage


Stage = Literal["plan", "research", "write", "quote_check", "review", "retry", "redact", "respond"]


class TraceEvent(BaseModel):
    stage: Stage
    kind: str  # "started", "finished", "tool_call", ...
    data: dict[str, Any]
    elapsed: float  # seconds since the request started
