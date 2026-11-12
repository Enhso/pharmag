# Property-test review findings

- **Date:** 2026-11-12
- **Scope:** All 47 entries in [the property catalogue](PROPERTIES.md), together with their implementations and generators.
- **Status:** **Open / proposed.** These are review findings and recommendations, not owner-approved contracts or implementation changes. The current authorization is to save this record only.
- **Tracking:** F01–F07 are HIGH severity; F08–F16 are MEDIUM severity. All 16 findings remain open.
- **Authority:** This file is the authoritative detailed record of this review, linked from [the handoff](../docs/handoff.md).

## Overall assessment

The catalogue **partially meets the five desiderata**:

1. **Non-tautology:** No unconditional tautology was found. Some expectations or constants come from the system under test (SUT), however, which weakens their independence.
2. **Discriminative power:** This is the largest weakness. Several properties accept materially weaker behavior, lack positive witnesses, or check consistency without pinning the intended contract.
3. **Orthogonality:** Coverage, fidelity, ordering, normalization, and symmetry are generally separated usefully.
4. **Generator relevance:** Mixed. Some generators exercise the intended domain well; others avoid important boundaries or rarely reach the behavior named by the property.
5. **Shrinking:** Synthetic inputs mostly shrink well. Sampling a real corpus, conditional checks that disable assertions, and fixed-length masks provide weaker counterexamples.

Keep the bulk of the catalogue and strengthen it rather than replacing it wholesale. In particular, distinguish an implementation-consistency check from an independently specified behavioral oracle.

## Evidence conventions

- **VERIFIED — prior review:** A temporary in-memory mutation survived the stated targeted suite. These experiments were performed during the prior review, not rerun while saving this file.
- **INSPECTION:** A conclusion from reading the catalogue, tests, implementation, or generators; it is not a mutation-test result or an observed application failure.
- A surviving targeted mutant is evidence of a test gap, **not** proof that the complete suite accepts the mutant, that the current application has that defect, or that the proposed replacement contract is approved.
- Owner decisions are explicitly called out where the intended behavior is unresolved. Recommendations below must not silently settle those decisions.

## Findings index

| ID  | Severity | Affected catalogue entries / area | Finding                                                                                                          | Status          |
| --- | -------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------- |
| F01 | HIGH     | 3, 11; secondary gap in 4         | Non-disclosure wording is infeasible literally; successful responses and protected-value coverage are incomplete | Open / proposed |
| F02 | HIGH     | T6–T7                             | Extraction completeness expectations are derived from the extracted data                                         | Open / proposed |
| F03 | HIGH     | I1–I4, T2–T3                      | Missing positive witnesses, self-reported rank antecedents, and collision-wide skipping weaken discrimination    | Open / proposed |
| F04 | HIGH     | 17                                | Chunk-cap assertion imports the implementation constant and misses oversized lines                               | Open / proposed |
| F05 | HIGH     | R1–R4                             | Window properties do not pin exact window geometry                                                               | Open / proposed |
| F06 | HIGH     | R6–R7                             | Cache checks do not establish mixed-hit behavior or disk persistence                                             | Open / proposed |
| F07 | HIGH     | I5                                | Unconditional unit-length wording conflicts with preserved zero rows                                             | Open / proposed |
| F08 | MEDIUM   | 1–2, 5–6                          | Configuration generators omit valid and whitespace boundary cases                                                | Open / proposed |
| F09 | MEDIUM   | 7–10                              | API validation matrix omits partial configurations and body/configuration combinations                           | Open / proposed |
| F10 | MEDIUM   | 12–13                             | Static asset checks miss reference forms and do not establish page wiring                                        | Open / proposed |
| F11 | MEDIUM   | 14, 18–19                         | Parser reference shares grammar assumptions and misses a source-placement discrepancy                            | Open / proposed |
| F12 | MEDIUM   | 22–23                             | Table overlap is weaker than containment; emitted-section inventory cannot reveal omissions                      | Open / proposed |
| F13 | MEDIUM   | R5                                | Substring checks allow empty text and do not establish coverage                                                  | Open / proposed |
| F14 | MEDIUM   | I6                                | Adapter checks omit active concurrency and model forwarding                                                      | Open / proposed |
| F15 | MEDIUM   | T1–T2                             | ID-only selection checks miss payload fidelity; interaction relevance is underspecified                          | Open / proposed |
| F16 | MEDIUM   | T4–T5                             | Arbitrary filters commonly bypass the query path; unknown classification depends on the resolver                 | Open / proposed |

## Detailed findings

### F01 — HIGH — Non-disclosure needs a feasible contract and complete response coverage

**Affected:** Properties 3 and 11, with a secondary scope gap in property 4. See [the catalogue](PROPERTIES.md), [`test_config.py:76`](test_config.py#L76), and [the API tests](test_api.py).

**INSPECTION:** Literally prohibiting any environment value from appearing as a substring is impossible for an empty value, and can also be impossible when a value collides with a variable name that must appear in diagnostics. The configuration test checks distinctive sentinels, not every environment value. Successful `/ask` responses lack an absence assertion. Property 4 checks `repr`, not `str` or printing.

**VERIFIED — prior review:** Adding the configured API key to a successful `/ask` response in memory still allowed all **11 API tests** to pass. This demonstrates a missing assertion; it is not an observed leak in the unchanged application.

**Proposed direction:** Define non-disclosure in terms of not exposing protected values, with distinctive secret tokens in valid and defective configurations. Inspect complete responses, including successful responses, rather than selected error fields alone.

**Owner decision needed:** Confirm the protected-value contract and whether property 4 is intended to cover `repr` only or also `str` / printing. Do not adopt literal arbitrary-value substring exclusion as though it were feasible.

### F02 — HIGH — T6/T7 extraction completeness lacks independent source oracles

**Affected:** T6–T7; [`test_tools.py:13–17`](test_tools.py#L13).

**INSPECTION:** Test data comes from `TOOLS.brands` and `TOOLS.glossary`; the expected T7 passage also comes from that same glossary. Partial extraction omissions remove the corresponding questions from the tests, and incorrect extracted content can become the expected content.

These remain meaningful **lookup-consistency** checks. They are not unconditional tautologies, but they do not independently establish extraction completeness or source fidelity.

**Proposed direction:** Generate miniature source documents while independently recording brand mappings and glossary definitions plus source ranges. Assert against those records. Do not clone the production extraction regex as the oracle.

### F03 — HIGH — Positive witnesses and independent ranking checks are missing

**Affected:** I1–I4 and T2–T3; [`test_index.py:102`](test_index.py#L102) and [the tool tests](test_tools.py).

**INSPECTION:** Returning `[]` satisfies I1–I3 in isolation; returning no interactions satisfies T2–T3 in isolation. Other tests reject globally empty implementations, so this is **not** a claim that an always-empty implementation survives the full suite.

I3 uses self-reported ranks as the antecedent for its assertion. I4 returns early on **any** vector collision, skipping checks for all chunks rather than isolating the ambiguous case.

**VERIFIED — prior review:** Doubling the BM25 contribution in memory still allowed all **11 index tests** to pass. This shows that the weighting is not pinned by those tests; it does not establish which weighting should be required.

**Proposed direction:** Use independently known matching IDs; include a non-first, known unique winner for both vector and lexical retrieval. Add independent positive and negative interaction witnesses. Test ties separately instead of skipping the entire case on a collision.

**Owner decision needed:** Confirm whether the weighting formula is part of the contract before adding assertions for a particular weighting.

### F04 — HIGH — Property 17 can follow an incorrect implementation cap

**Affected:** Property 17; [`test_corpus.py:83`](test_corpus.py#L83).

**INSPECTION:** The assertion imports `MAX_CHARS` from the implementation instead of independently asserting the documented **5000-character** limit. The generator limits a single line to 3000 characters, so it cannot produce a single line exceeding 5000.

**VERIFIED — prior review:** Changing the cap from **5000 to 50000** in memory still allowed all **17 corpus tests** to pass.

**Proposed direction:** Assert the documented cap independently. Generate joined lengths of **4999, 5000, and 5001**, accounting for newlines and blank gaps, and generate oversized single lines. Cover both aggregation boundaries and the single-line case.

### F05 — HIGH — R1–R4 admit undersized windows

**Affected:** R1–R4; [the retrieval tests](test_retrieval_eval.py).

**INSPECTION:** Coverage, maximum length, overlap, and line ownership do not by themselves require the requested window size.

**VERIFIED — prior review:** Using an effective size of `max(overlap + 1, size - 1)` in memory still allowed all **7 retrieval tests** to pass. A witness is text `aaaaaa`, `size=3`, `overlap=0`, producing ranges `[(0, 2), (2, 4), (4, 6)]`.

**Proposed direction:** Add structural assertions that every non-final window has length `size`, consecutive starts differ by `size - overlap`, the final end equals the text length, and empty input produces `[]`. Specify these independently rather than cloning the implementation loop.

### F06 — HIGH — R6/R7 do not establish persistent cache behavior

**Affected:** R6–R7; [the retrieval tests](test_retrieval_eval.py).

**INSPECTION:** The checks exercise an all-miss batch followed by an identical all-hit batch and a model switch. They do not exercise mixed hits, reconstruction of the cache object, or persistence across reconstruction. Both model fakes return identical outputs, weakening model-isolation checks.

**VERIFIED — prior review:** A memory-only cache still allowed all **7 retrieval tests** to pass. Disk persistence is intended by the current class documentation, but is not proven by these two properties.

**Proposed direction:** Use a reference dictionary keyed by `(model, text)` and stateful sequences such as `[a, a]`, then `[b, a, b]`, reconstruction with the same model, switching models and switching back, permutations, and empty batches. Compare returned rows and exact underlying embedding calls. Use model-tagged vectors so cross-model contamination is observable.

### F07 — HIGH — I5 must distinguish zero rows from normalizable rows

**Affected:** I5; [`src/pharmag/index.py:70–75`](../src/pharmag/index.py#L70).

**INSPECTION:** The unconditional unit-length property conflicts with implementation behavior that preserves zero rows. The fake produces nonnegative values, and metadata ensures stored inputs are nonzero, so signed-vector and zero-row failures are absent from the generated cases.

**Owner decision needed:** Decide whether zero vectors should be rejected, preserved, or excluded by an explicit precondition before rewriting the property.

**Proposed direction:** Generate zero vectors, signed basis vectors, antipodal vectors, and positive multiples. Apply unit-length and scaling assertions only under the agreed contract.

### F08 — MEDIUM — Configuration generators miss valid and whitespace boundaries

**Affected:** Properties 1–2 and 5–6; [the configuration tests](test_config.py).

**INSPECTION:** Missing cases include valid `http://` URLs, short valid values, whitespace-only values, and Unicode edge whitespace. The negative typo case is a single fixture.

**Proposed direction:** Separate preservation of all-valid configurations from missing-target checks. Generate independently known distant variable names for negative cases as well as typo cases.

**Contract caveat:** Do not assume stricter RFC URL validation than the existing intended contract.

### F09 — MEDIUM — API validation needs a configuration/body cross-product

**Affected:** Properties 7–10; [the API tests](test_api.py).

**INSPECTION:** Tests cover valid, all-bad, and absent configurations, but not partial configurations. The malformed-body `422` check runs only with good configuration, despite catalogue prose describing behavior regardless of configuration.

**Proposed direction:** Cross configuration subsets with body shapes, including `null` and a minimal string, to establish validation behavior and precedence.

**Contract caveat:** Whitespace-only input is currently nonempty under `min_length`. Do not silently change the contract from nonempty to nonblank.

### F10 — MEDIUM — Asset checks do not establish actual same-origin wiring

**Affected:** Properties 12–13; [the API tests](test_api.py).

**INSPECTION:** The regex misses protocol-relative references such as `//CDN.EXAMPLE/app.js` and dynamic URLs. Independent asset GET requests establish availability, not that the page actually references and loads those assets correctly.

**Proposed direction:** Parse page references and resolve them against the page origin. Use browser request interception where dynamic loads must be covered.

**Evidence caveat:** This is a test-coverage gap, not an observation that the current application makes external requests.

### F11 — MEDIUM — Parser reference and generator share limiting assumptions

**Affected:** Properties 14 and 18–19; [the corpus tests](test_corpus.py).

**INSPECTION:** The useful reference shares the heading grammar with production. Source placement differs: the reference considers `n <= 3`, while production allows placement through 5 before the heading. The generator hides that discrepancy.

**Proposed direction:** Generate labelled document events before rendering text, so expectations are independent of parser recognition. Include level-6 headings and multiple files.

**Owner decision needed:** Resolve the intended source-placement behavior rather than silently choosing the reference or production interpretation.

### F12 — MEDIUM — Table containment and section inventory need independent checks

**Affected:** Properties 22–23; [the corpus tests](test_corpus.py).

**INSPECTION:** The table assertion requires one overlapping chunk, not a chunk containing the complete table. Section inventory is derived from emitted chunks, making omitted sections and incorrect non-null keys invisible.

**Proposed direction:** Require complete table containment using an independently known source slice, and compare emitted sections against an independent heading/key inventory.

**Scope caveat:** Keep the table claim scoped to current real-table sizes; do not infer a contract for arbitrary oversized tables.

### F13 — MEDIUM — R5 substring fidelity does not imply nonempty coverage

**Affected:** R5; [the retrieval tests](test_retrieval_eval.py).

**INSPECTION:** Substring containment accepts empty chunk text and does not reveal omitted content.

**Proposed direction:** Require nonempty chunks and per-file coverage. Use synthetic files with exact expected slices, plus real-corpus integration coverage.

### F14 — MEDIUM — I6 does not measure active concurrency or model forwarding

**Affected:** I6; [the index tests](test_index.py).

**INSPECTION:** Existing checks establish ordering and a batch bound, not peak active concurrency or forwarding of the requested model.

**Proposed direction:** Record the model and peak active calls. Use controlled schedules rather than millisecond sleeps so ordering and concurrency assertions are deterministic.

### F15 — MEDIUM — Tool selection needs payload fidelity and meaningful interaction witnesses

**Affected:** T1–T2; [the tool tests](test_tools.py).

**INSPECTION:** ID-only selection assertions do not establish payload fidelity. T2 checks substring presence, not relevance to the requested drug; `matched=("",)` satisfies that substring check.

**Proposed direction:** Check provenance and payload as well as IDs. Use independently known positive mentions and negative controls, with approved alias/class terms and explicit word-matching semantics.

**Contract caveat:** Do not assume new ranking or truncation rules while strengthening these assertions.

### F16 — MEDIUM — Tool filters usually miss the intended query path

**Affected:** T4–T5; [the tool tests](test_tools.py).

**INSPECTION:** Arbitrary filters commonly cause an early exit before the query path. The resolver under test also classifies the unknown branch, reducing oracle independence. The existing `assume` excludes only a tiny known set; this is not severe over-filtering.

**Proposed direction:** Separate valid-filter cases with arbitrary queries from invalid-filter diagnostic cases. Use independently known invalid names instead of asking the resolver under test to decide which branch should be expected.

## Generator relevance and shrinking

### Existing coverage to retain

The current generators already allow `k=0`, empty window text, empty cache batches, Unicode, and NUL. Do not describe these as missing or add duplicate coverage under that assumption.

### Missing or weakly exercised domains

- **Index and retrieval:** Empty indexes, empty/tokenless queries, signed and zero vectors, and ties.
- **Parser:** Exact cap boundaries, oversized single lines, level-6 headings, and multiple files.
- **Embedding adapter:** Batch and concurrency boundaries with enough work to actually exercise the bound.
- **Tools:** Synthetic positive and negative mentions, regex-special characters, and valid filters that reach the query path.

Generate negatives and `None` only where they are in the supported domain or where rejection is documented. The handling of negative `k`, invalid batch sizes, and invalid concurrency remains an owner decision, not an implied new contract.

### Shrinking caveats

- Synthetic document inputs mostly shrink well; selecting a real-corpus sample does not shrink the document itself.
- I4 collisions disable the entire check rather than producing a focused tie example.
- Distinctive sentinels are useful for non-disclosure, but the sentinel construction prevents short-value cases; keep the purposes separate.
- A fixed **60-boolean** case mask includes irrelevant bits and truncates names longer than 60 characters. Use a case mask whose length matches the generated name.

## Property patterns to keep or strengthen

### Strong existing patterns

Conservation in property 14, fidelity in 15, disjointness in 16, and R4's independent line oracle are useful invariants with relatively easy-to-verify expectations. Preserve that structure.

### Independent oracles

Use labelled configurations for configuration behavior, independent selection expectations, generated source documents for extraction, and a reference cache model for stateful cache behavior. Avoid deriving the expected inventory or contract constant from the SUT.

### Symmetry and idempotence

T3's symmetry check is useful but needs positive witnesses so an empty result cannot satisfy it alone. Useful idempotence checks include resolving an already resolved valid generic name and verifying that an all-hit cache batch performs no additional embeddings.

### Metamorphic relations

Candidates to strengthen coverage, subject to the relevant contracts, include:

- LF/CRLF equivalence.
- Generic/brand equivalence.
- Invariance under unrelated, non-`OPENAI` environment variables.
- Positive vector-scaling invariance for nonzero finite vectors.

There is no natural lossless encode/decode pair here: the parser drops headings and metadata. Do not force a round-trip property onto a deliberately lossy transformation.

## Prior validation record — not rerun for this save

The prior review finished against the unchanged application with **67 tests passing**:

```sh
UV_CACHE_DIR=/tmp/pharmag-review-uv-cache uv run --locked --offline pytest -q
```

Five separate temporary **in-memory** mutants survived their targeted suites:

| Finding | Temporary mutation                                         | Targeted result          |
| ------- | ---------------------------------------------------------- | ------------------------ |
| F01     | Add the configured API key to a successful `/ask` response | 11 API tests passed      |
| F03     | Double the BM25 contribution                               | 11 index tests passed    |
| F06     | Replace persistent cache behavior with memory-only caching | 7 retrieval tests passed |
| F05     | Use effective window size `max(overlap + 1, size - 1)`     | 7 retrieval tests passed |
| F04     | Raise the chunk cap from 5000 to 50000                     | 17 corpus tests passed   |

These were targeted experiments, **not a full mutation campaign**. They do not demonstrate real leaks or those defects in the unchanged application. Production and test sources were untouched by the review. No tests or mutation experiments were run as part of saving this document.

## Suggested next-agent sequence

1. **Clarify contracts with the owner first.** In particular: protected values and formatting surfaces (F01), weighting (F03), zero vectors (F07), source placement (F11), and any unsupported-input behavior. Do not adopt proposed contracts merely because they appear in this review.
2. **Add independent oracles and positive witnesses.** Prioritize extraction completeness, known retrieval winners, and nonempty interaction examples (F02–F03), then selection/provenance checks where relevant.
3. **Pin cap, window geometry, and cache behavior.** Strengthen F04–F06 against independently stated contracts and stateful examples.
4. **Cover the remaining boundaries and wiring.** Address configuration/body matrices, parser inventories, coverage, concurrency/model forwarding, tool filters, and actual asset references (F08–F16).
5. **Update the catalogue together with the tests after owner confirmation.** Retain the useful existing invariants, distinguish consistency checks from independent oracles, and verify that strengthened tests kill the relevant mutants. Track progress using F01–F16.

Recording these findings does not authorize fixes, contract adoption, or catalogue changes.
