import asyncio
from pathlib import Path

import pydantic_ai.models
import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from fakes import FakeEmbedder
from pharmag.agents import BUDGET_MESSAGE, RoleModels
from pharmag.corpus import load_corpus
from pharmag.grounding import dangling_markers
from pharmag.index import Index
from pharmag.models import (
    Citation,
    Claim,
    ClaimVerdict,
    Draft,
    Finding,
    Findings,
    Plan,
    Review,
    SubQuestion,
)
from pharmag.pipeline import DISCLAIMER, MAX_TOOL_CALLS, NOTHING_SUPPORTED, Engine, PipelineError, answer
from pharmag.tools import Tools

pydantic_ai.models.ALLOW_MODEL_REQUESTS = False

CHUNKS = load_corpus(Path(__file__).parent.parent / "corpus")
TOOLS = Tools(CHUNKS, asyncio.run(Index.build(CHUNKS, FakeEmbedder())))
BY_ID = {c.id: c for c in CHUNKS}

QUESTION = "What are the contraindications of warfarin?"
PLAN = Plan(
    in_scope=True,
    reason="A label question.",
    sub_questions=[SubQuestion(text="What are warfarin's contraindications?", drugs=["warfarin"])],
)


def passage(drug):
    p = TOOLS.get_section(drug, "contraindications").passages[0]
    return p, " ".join(p.text.split()[:8])


WARFARIN, WARFARIN_QUOTE = passage("warfarin")
APIXABAN, APIXABAN_QUOTE = passage("apixaban")
FINDINGS = Findings(
    findings=[Finding(statement="A contraindication.", chunk_id=WARFARIN.chunk_id, quote=WARFARIN_QUOTE)],
    not_found="",
)
GOOD = Claim(text="Warfarin has contraindications.", kind="fact", citations=[Citation(chunk_id=WARFARIN.chunk_id, quote=WARFARIN_QUOTE)])
PLANTED = Claim(
    text="Apixaban is contraindicated in moon dust allergy.",
    kind="fact",
    citations=[Citation(chunk_id=APIXABAN.chunk_id, quote="contraindicated in moon dust allergy")],
)
PROSE = "Warfarin has contraindications [1]. Apixaban is contraindicated in moon dust allergy [2]."
BOTH = Draft(answer=PROSE, claims=[GOOD, PLANTED])
REAL_APIXABAN = Claim(
    text="Apixaban has contraindications.", kind="fact", citations=[Citation(chunk_id=APIXABAN.chunk_id, quote=APIXABAN_QUOTE)]
)
BOTH_REAL = Draft(answer="Warfarin has contraindications [1]. Apixaban has contraindications [2].", claims=[GOOD, REAL_APIXABAN])
ONLY_GOOD = Draft(answer="Warfarin has contraindications [1].", claims=[GOOD])


def supported(n):
    return Review(verdicts=[ClaimVerdict(claim=i, status="supported", reason="Stated.") for i in range(1, n + 1)], unmarked=[])


def scripted(*outputs):
    """A model that plays the outputs in order, repeating the last. A str answers a call with no output tool; an Exception is raised."""
    calls = []

    def play(messages, info):
        out = outputs[min(len(calls), len(outputs) - 1)]
        calls.append(messages)
        if isinstance(out, Exception):
            raise out
        if isinstance(out, str):
            return ModelResponse(parts=[TextPart(out)])
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, out.model_dump())])

    return FunctionModel(play), calls


def researcher(*first_turn_tools):
    """A worker that calls the tools in one turn, then returns the findings."""
    runs = []

    def play(messages, info):
        if any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, FINDINGS.model_dump())])
        runs.append(messages)
        return ModelResponse(parts=[ToolCallPart(name, args) for name, args in first_turn_tools])

    return FunctionModel(play), runs


WARFARIN_SECTION = ("get_section", {"drug": "warfarin", "section": "contraindications"})
APIXABAN_SECTION = ("get_section", {"drug": "apixaban", "section": "contraindications"})


def run(planner, worker, writer, critic, emit=None):
    engine = Engine(TOOLS, BY_ID, RoleModels(planner, worker, writer, critic))
    return asyncio.run(answer(QUESTION, engine, emit))


def test_happy_path_cites_the_file_and_ends_with_the_disclaimer():
    events = []
    worker, runs = researcher(WARFARIN_SECTION)
    writer, writes = scripted(ONLY_GOOD)
    critic, reviews = scripted(supported(1))
    r = run(scripted(PLAN)[0], worker, writer, critic, events.append)
    assert r.sources == [WARFARIN.file]
    assert "Sources:\n[1] " + WARFARIN.file in r.answer
    assert r.answer.endswith(DISCLAIMER) and r.disclaimer == DISCLAIMER
    assert (len(runs), len(writes), len(reviews), r.critic.review_rounds, r.critic.marker_check) == (1, 1, 1, 1, "passed")
    assert [t.tool for t in r.tool_calls] == ["get_section"]
    assert r.tool_calls[0].hits[0].chunk_id == WARFARIN.chunk_id
    assert {"plan", "research", "write", "quote_check", "review", "respond"} <= {e.stage for e in events}
    assert any(e.kind == "tool_call" for e in events)
    assert "total" in r.timings and set(r.usage.by_role) == {"planner", "worker", "writer", "critic"}
    assert r.usage.requests == sum(u.requests for u in r.usage.by_role.values())


def test_a_planted_quote_is_caught_without_the_critic_and_redacted_after_one_retry():
    worker, runs = researcher(WARFARIN_SECTION, APIXABAN_SECTION)
    writer, writes = scripted(BOTH, BOTH, "Warfarin has contraindications [1].")
    critic, _ = scripted(supported(2))  # the critic is fooled; the quote check must not be
    r = run(scripted(PLAN)[0], worker, writer, critic)
    assert len(runs) == 2  # the planned worker and one follow-up worker
    assert len(writes) == 3  # draft, revision, redaction
    assert r.critic.review_rounds == 2
    assert [v.status for v in r.critic.verdicts] == ["supported", "unsupported"]
    assert [x.text for x in r.critic.removed] == [PLANTED.text]
    assert "quote" in r.critic.removed[0].reason
    assert "[2]" not in r.answer and "moon dust" not in r.answer
    assert r.sources == [WARFARIN.file]


def test_a_follow_up_that_the_retry_fixes_needs_no_redaction():
    worker, runs = researcher(WARFARIN_SECTION)
    writer, writes = scripted(ONLY_GOOD, ONLY_GOOD)
    unsupported = Review(
        verdicts=[ClaimVerdict(claim=1, status="unsupported", reason="Too broad.", follow_up="warfarin contraindications")],
        unmarked=[],
    )
    critic, reviews = scripted(unsupported, supported(1))
    r = run(scripted(PLAN)[0], worker, writer, critic)
    assert len(runs) == 2 and runs[1][0].parts[-1].content == "warfarin contraindications"
    assert len(writes) == 2 and len(reviews) == 2  # no redaction call
    assert r.critic.removed == [] and r.sources == [WARFARIN.file] and "[1]" in r.answer


def test_a_worker_whose_quote_is_not_in_the_passage_is_sent_back_inside_the_same_call():
    bad = Findings(
        findings=[Finding(statement="x", chunk_id=WARFARIN.chunk_id, quote="words that are not there at all")], not_found=""
    )
    worker_calls = []

    def play(messages, info):
        worker_calls.append(messages)
        if any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            findings = FINDINGS if len(worker_calls) > 2 else bad  # the retry prompt comes after the bad answer
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, findings.model_dump())])
        return ModelResponse(parts=[ToolCallPart(*WARFARIN_SECTION)])

    r = run(scripted(PLAN)[0], FunctionModel(play), scripted(ONLY_GOOD)[0], scripted(supported(1))[0])
    assert len(worker_calls) == 3  # tool call, bad findings, corrected findings
    sent = str(worker_calls[2][-1].parts[0].content)
    assert WARFARIN.chunk_id in sent and "words that are not there" in sent and "word for word" in sent
    assert r.usage.by_role["worker"].requests == 3


def test_a_worker_that_keeps_a_bad_quote_still_returns_and_stage_four_marks_the_claim():
    bad = Findings(findings=[Finding(statement="x", chunk_id=WARFARIN.chunk_id, quote="not there at all")], not_found="")
    calls = []

    def play(messages, info):
        calls.append(1)
        if any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, bad.model_dump())])
        return ModelResponse(parts=[ToolCallPart(*WARFARIN_SECTION)])

    badclaim = Draft(
        answer="Warfarin has contraindications [1].",
        claims=[GOOD.model_copy(update={"citations": [Citation(chunk_id=WARFARIN.chunk_id, quote="not there at all")]})],
    )
    r = run(scripted(PLAN)[0], FunctionModel(play), scripted(badclaim, badclaim, "Nothing here.")[0], scripted(supported(1))[0])
    assert len(calls) == 8  # two workers (planned, follow-up), each: tool call, first try, two output retries
    assert [x.text for x in r.critic.removed] == [GOOD.text]


def test_an_out_of_scope_question_gets_a_refusal_and_calls_nobody_else():
    refuse = Plan(in_scope=False, reason="The question is about cooking.", sub_questions=[])
    worker, runs = researcher()
    writer, writes = scripted(ONLY_GOOD)
    critic, reviews = scripted(supported(1))
    r = run(scripted(refuse)[0], worker, writer, critic)
    assert (runs, writes, reviews) == ([], [], [])
    assert "cooking" in r.answer and r.answer.endswith(DISCLAIMER)
    assert r.sources == [] and r.critic.review_rounds == 0 and r.tool_calls == []


def test_a_worker_over_its_tool_budget_gets_the_budget_message_and_still_returns_findings():
    seen = []

    def greedy(messages, info):
        returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
        if returns and BUDGET_MESSAGE in returns[-1].content:
            seen.append(returns[-1].content)
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, FINDINGS.model_dump())])
        return ModelResponse(parts=[ToolCallPart(*WARFARIN_SECTION)])

    writer, _ = scripted(ONLY_GOOD)
    critic, _ = scripted(supported(1))
    r = run(scripted(PLAN)[0], FunctionModel(greedy), writer, critic)
    assert seen and len(r.tool_calls) == MAX_TOOL_CALLS
    assert r.sources == [WARFARIN.file]


def test_a_dangling_marker_left_by_the_redaction_is_repaired():
    worker, _ = researcher(WARFARIN_SECTION, APIXABAN_SECTION)
    writer, _ = scripted(BOTH, BOTH, "Warfarin has contraindications [1]. Moon dust is a problem [2].")
    critic, _ = scripted(supported(2))
    r = run(scripted(PLAN)[0], worker, writer, critic)
    assert r.critic.marker_check == "repaired"
    assert dangling_markers(r.answer, {1}) == [] and "Moon dust" not in r.answer


TWO_SENTENCES = "Warfarin has contraindications [1]. It also has others [1]."
MISMATCHED = Draft(answer=TWO_SENTENCES + " Extra [2][3].", claims=[GOOD])
CONSISTENT = Draft(answer=TWO_SENTENCES, claims=[GOOD])


def test_the_writer_repairs_markers_without_claims_inside_one_run():
    worker, _ = researcher(WARFARIN_SECTION)
    writer, writes = scripted(MISMATCHED, CONSISTENT)
    r = run(scripted(PLAN)[0], worker, writer, scripted(supported(1))[0])
    assert len(writes) == 2 and r.critic.review_rounds == 1
    assert r.critic.marker_check == "passed"
    assert "It also has others" in r.answer
    assert "markers [2, 3]" in str(writes[1][-1].parts[0].content) and "1 claims" in str(writes[1][-1].parts[0].content)


def test_a_stubborn_marker_mismatch_still_answers_and_is_repaired():
    worker, _ = researcher(WARFARIN_SECTION)
    writer, writes = scripted(MISMATCHED)
    r = run(scripted(PLAN)[0], worker, writer, scripted(supported(1))[0])
    assert len(writes) == 3  # first try and two output retries, then it goes through
    assert r.critic.marker_check == "repaired" and dangling_markers(r.answer, {1}) == []
    assert "It also has others" in r.answer and "Extra" not in r.answer


def broken(messages, info):
    raise RuntimeError("model down")


def test_one_failed_worker_does_not_fail_the_request():
    two = PLAN.model_copy(update={"sub_questions": [*PLAN.sub_questions, SubQuestion(text="BROKEN", drugs=[])]})
    healthy, _ = researcher(WARFARIN_SECTION)

    def play(messages, info):
        if "BROKEN" in str(messages[0].parts[-1].content):
            raise RuntimeError("model down")
        return healthy.function(messages, info)

    writer, writes = scripted(ONLY_GOOD)
    r = run(scripted(two)[0], FunctionModel(play), writer, scripted(supported(1))[0])
    sent = writes[0][0].parts[-1].content
    assert "RuntimeError" in sent and "model down" not in sent  # the message could echo a key
    assert r.sources == [WARFARIN.file]


def test_the_request_fails_when_every_worker_fails():
    writer, writes = scripted(ONLY_GOOD)
    with pytest.raises(PipelineError) as failure:
        run(scripted(PLAN)[0], FunctionModel(broken), writer, scripted(supported(1))[0])
    assert failure.value.stage == "research" and not writes


def unsupported(follow_up="warfarin contraindications", claim=1):
    return Review(verdicts=[ClaimVerdict(claim=claim, status="unsupported", reason="Too broad.", follow_up=follow_up)], unmarked=[])


def test_a_redactor_that_drops_the_marker_but_keeps_the_sentence_does_not_get_it_through():
    worker, _ = researcher(WARFARIN_SECTION, APIXABAN_SECTION)
    kept = "Warfarin has contraindications [1]. Apixaban is contraindicated in moon dust allergy."
    r = run(scripted(PLAN)[0], worker, scripted(BOTH, BOTH, kept)[0], scripted(supported(2))[0])
    assert r.critic.marker_check == "repaired" and "moon dust" not in r.answer and "[1]" in r.answer


def test_an_unmarked_statement_triggers_the_retry_and_is_removed_when_it_persists():
    draft = Draft(answer="Warfarin has contraindications [1]. Warfarin is also dangerous.", claims=[GOOD])
    worker, runs = researcher(WARFARIN_SECTION)
    writer, writes = scripted(draft, draft, draft.answer)  # the redactor returns the draft's prose untouched
    review = Review(verdicts=supported(1).verdicts, unmarked=["Warfarin is also dangerous."])
    r = run(scripted(PLAN)[0], worker, writer, scripted(review)[0])
    assert runs[1][0].parts[-1].content == "Warfarin is also dangerous." and len(writes) == 3
    assert r.critic.marker_check == "repaired" and r.critic.unmarked == review.unmarked
    assert "dangerous" not in r.answer and "[1]" in r.answer


@pytest.mark.parametrize("failing", ["worker", "writer"])
def test_a_failed_retry_round_ships_the_first_draft_with_the_flags_redacted(failing):
    healthy, _ = researcher(WARFARIN_SECTION, APIXABAN_SECTION)

    def play(messages, info):
        if "moon dust" in str(messages[0].parts[-1].content):  # only the follow-up worker asks about the planted claim
            raise RuntimeError("model down")
        return healthy.function(messages, info)

    redacted = "Warfarin has contraindications [1]."
    writer = scripted(BOTH, RuntimeError("model down"), redacted)[0] if failing == "writer" else scripted(BOTH, redacted)[0]
    r = run(scripted(PLAN)[0], FunctionModel(play) if failing == "worker" else healthy, writer, scripted(supported(2))[0])
    assert r.critic.review_rounds == 1 and [x.text for x in r.critic.removed] == [PLANTED.text]
    assert "[1]" in r.answer and "moon dust" not in r.answer


def test_an_in_scope_plan_without_sub_questions_researches_the_question_itself():
    worker, runs = researcher(WARFARIN_SECTION)
    r = run(scripted(PLAN.model_copy(update={"sub_questions": []}))[0], worker, scripted(ONLY_GOOD)[0], scripted(supported(1))[0])
    assert len(runs) == 1 and runs[0][0].parts[-1].content == QUESTION and r.sources == [WARFARIN.file]


@pytest.mark.parametrize("order", [("supported", "unsupported"), ("unsupported", "supported")])
def test_the_worst_of_two_verdicts_for_one_claim_wins(order):
    verdicts = [ClaimVerdict(claim=1, status=s, reason="r", follow_up="warfarin contraindications") for s in order]
    worker, _ = researcher(WARFARIN_SECTION)
    r = run(scripted(PLAN)[0], worker, scripted(ONLY_GOOD, ONLY_GOOD, "Nothing here.")[0], scripted(Review(verdicts=verdicts, unmarked=[]))[0])
    assert [v.status for v in r.critic.verdicts] == ["unsupported"] and len(r.critic.removed) == 1


def test_a_sentence_kept_by_the_redactor_for_a_removed_claim_leaves_the_answer_with_only_the_notice():
    worker, _ = researcher(WARFARIN_SECTION)
    writer = scripted(ONLY_GOOD, ONLY_GOOD, ONLY_GOOD.answer)[0]
    r = run(scripted(PLAN)[0], worker, writer, scripted(unsupported())[0])
    assert r.answer.startswith(NOTHING_SUPPORTED) and r.answer.endswith(DISCLAIMER)
    assert "Sources:" not in r.answer and r.sources == [] and len(r.critic.removed) == 1


def test_blank_follow_ups_and_blank_unmarked_strings_start_no_retry_round():
    worker, runs = researcher(WARFARIN_SECTION)
    review = Review(verdicts=unsupported("  ").verdicts, unmarked=[" "])
    r = run(scripted(PLAN)[0], worker, scripted(ONLY_GOOD, "Fine.")[0], scripted(review)[0])
    assert len(runs) == 1 and r.critic.review_rounds == 1


def test_an_ambiguous_verdict_keeps_the_claim_and_adds_a_cautions_block():
    ambiguous = Review(verdicts=[ClaimVerdict(claim=1, status="ambiguous", reason="Needs a clinician.")], unmarked=[])
    worker, _ = researcher(WARFARIN_SECTION)
    writer, writes = scripted(ONLY_GOOD)
    r = run(scripted(PLAN)[0], worker, writer, scripted(ambiguous)[0])
    assert len(writes) == 1 and "[1]" in r.answer and r.sources == [WARFARIN.file]
    assert [(c.marker, c.reason) for c in r.critic.cautions] == [(1, "Needs a clinician.")]
    assert "Cautions:\n[1] Needs a clinician." in r.answer


def test_a_claim_the_critic_gave_no_verdict_is_treated_as_unsupported():
    worker, _ = researcher(WARFARIN_SECTION)
    r = run(scripted(PLAN)[0], worker, scripted(ONLY_GOOD, ONLY_GOOD, "Nothing here.")[0], scripted(Review(verdicts=[], unmarked=[]))[0])
    assert [(v.status, v.reason) for v in r.critic.verdicts] == [("unsupported", "The critic gave no verdict.")]
    assert [x.text for x in r.critic.removed] == [GOOD.text]


def test_a_cited_chunk_that_no_tool_returned_in_this_request_fails_the_quote_check():
    worker, _ = researcher(WARFARIN_SECTION)  # the apixaban passage is real but this request never fetched it
    writer = scripted(BOTH_REAL, BOTH_REAL, "Warfarin has contraindications [1].")[0]
    r = run(scripted(PLAN)[0], worker, writer, scripted(supported(2))[0])
    assert "no tool returned" in r.critic.removed[0].reason and APIXABAN.file not in r.sources


def test_sources_leave_out_the_file_of_a_claim_whose_marker_is_not_in_the_final_prose():
    worker, _ = researcher(WARFARIN_SECTION, APIXABAN_SECTION)
    draft = Draft(answer="Warfarin has contraindications [1].", claims=[GOOD, REAL_APIXABAN])
    r = run(scripted(PLAN)[0], worker, scripted(draft)[0], scripted(supported(2))[0])
    assert r.sources == [WARFARIN.file] and [c.marker for c in r.citations] == [1]
