# Properties

Each line says what must hold for every input of a kind, and names the test that checks it.
Hypothesis runs the config tests on many generated environments, so one line covers many cases.

## Config check (`load_settings`)

1. For any environment, the check reports exactly the required variables that are missing, empty, padded with whitespace, wrapped in a quote, or (for the base URL) lacking `http://` or `https://`, and exactly the override variables (`PHARMAG_*_MODEL`) that are set and have one of the same defects except being missing. It lists each at most once, in the fixed order API key, base URL, model, embedding model, planner, worker, writer, critic, and it ignores every other variable. `test_reports_exactly_the_defective_variables` (`tests/test_config.py`)
2. When every required variable and every set override is fine, the check returns the settings with the values exactly as given. It never trims, unquotes or otherwise repairs a value. A role whose override is unset gets the value of `OPENAI_MODEL`. `test_reports_exactly_the_defective_variables` (`tests/test_config.py`)
3. For any environment, no problem (variable name or text) contains any variable's value, so a bad value cannot leak through a response or a log. `test_no_problem_contains_a_value` (`tests/test_config.py`)
4. Printing the settings does not show the API key. `test_the_printed_settings_hide_the_key` (`tests/test_config.py`)
5. When a required variable is missing and the environment holds an `OPENAI_*` name that is the real name with one character deleted, the problem text names that near-miss. `test_a_misspelled_name_is_named_when_the_real_one_is_missing` (`tests/test_config.py`)
6. An unrelated `OPENAI_*` variable, or another required variable, is never offered as a misspelling. `test_other_openai_names_are_not_taken_for_misspellings` (`tests/test_config.py`)
C7. With the four required variables fine, no override set gives every role the model; a clean override is used as given for its own role only. `test_unset_overrides_take_the_model_and_clean_ones_are_used_as_given` (`tests/test_config.py`)
C8. A set but defective override (for example empty or quoted) is reported under its own name. `test_a_defective_override_is_reported_by_name` (`tests/test_config.py`)

## Search index (Index.search)

The index tests use a fake embedder that hashes words into 32 numbers, so they need no network. Hypothesis builds many random chunk lists and queries.

I1. Every returned chunk matches every filter given (`drug`, `source`, `section`). `test_every_hit_satisfies_every_filter` (`tests/test_index.py`)
I2. A search returns at most `k` hits, never the same chunk twice, and the scores never go up from one hit to the next. `test_at_most_k_distinct_hits_in_non_increasing_score_order` (`tests/test_index.py`)
I3. A chunk ranked first by the vector comparison and first by the keyword (BM25) ranking is the first result. `test_first_in_both_rankings_is_first_overall` (`tests/test_index.py`)
I4. Searching with a chunk's own embedding text ranks that chunk first by vector similarity, when no other chunk's vector points the same way. The fused result can still put another chunk first, because BM25 rewards a chunk that repeats the query's words. `test_a_chunks_own_text_ranks_it_first_by_similarity` (`tests/test_index.py`)
I5. Every stored embedding has length 1, so a dot product equals cosine similarity. `test_stored_rows_have_unit_length` (`tests/test_index.py`)
I6. `OpenAIEmbedder.embed` returns one row per text in input order, for any number of texts, batch size and concurrency, even when the server answers batches or rows out of order, and never sends a batch larger than the batch size. `test_openai_embedder_keeps_input_order` (`tests/test_index.py`)
I7. Building twice from the same chunks and searching gives identical results. `test_building_twice_gives_equal_results` (`tests/test_index.py`)
I8. Examples: a rare exact token ("CYP3A4") puts its one chunk first even when the vector ranking is no help (`test_a_rare_exact_token_wins_even_when_dense_does_not_help`); a drug filter drops other drugs (`test_a_drug_filter_excludes_other_drugs`); no matching candidates gives an empty list (`test_no_candidates_gives_an_empty_list`); a query sharing no word with a chunk gives it no keyword rank (`test_a_query_with_no_lexical_overlap_has_no_bm25_rank`) (`tests/test_index.py`)

## Server and page

7. The server starts and `GET /health` answers 200 whether the configuration is valid, defective or entirely absent. With valid configuration it reports `status` ok and the index state `building`, `ready` or `failed`; with defective configuration it reports `degraded` and starts no build. `test_health_is_ok_with_valid_config`, `test_a_defective_config_starts_no_build`, `test_health_is_degraded_but_200_with_invalid_config`, `test_server_starts_with_no_configuration_at_all` (`tests/test_api.py`)
8. With valid configuration and a built engine, `POST /ask` with a non-empty question answers 200 with the pipeline's `AskResponse` unchanged, every top-level field of the contract included. If the build is still running, the request waits for it. `test_ask_waits_for_the_build_and_returns_every_contract_field` (`tests/test_api.py`)
9. With defective configuration, `POST /ask` answers 503 and names each bad variable. `test_ask_is_503_and_names_the_bad_variables_with_invalid_config` (`tests/test_api.py`)
10. A body without a non-empty string `question` gets 422, whatever the configuration. `test_ask_rejects_a_malformed_body_with_422` (`tests/test_api.py`)
11. The API key value never appears in `/health` or `/ask` responses, including when the key is defective and when it occurs in the text of a build or pipeline exception. `test_health_is_degraded_but_200_with_invalid_config`, `test_ask_is_503_and_names_the_bad_variables_with_invalid_config`, `test_the_api_key_in_an_exception_text_never_reaches_a_response` (`tests/test_api.py`)
12. No file in the static folder refers to another host. `test_the_page_loads_nothing_from_another_host` (`tests/test_api.py`)
13. `GET /` serves the page and its CSS and JavaScript from the same server. `test_root_serves_the_page_and_its_assets` (`tests/test_api.py`)
S14. `/health` reports `building` while the engine build runs and `ready` after it. `test_health_says_building_while_the_build_is_held_then_ready` (`tests/test_api.py`)
S15. A build that fails 4 attempts leaves `/health` at `failed` with an `index_error`, and `/ask` gives 503 with `error` "index"; the next `/ask` starts a new build, which can succeed. `test_a_build_that_fails_every_attempt_gives_503_and_a_later_ask_rebuilds` (`tests/test_api.py`)
S16. A build that fails fewer than 4 attempts and then succeeds ends `ready`. `test_a_build_that_fails_twice_then_succeeds_ends_ready` (`tests/test_api.py`)
S17. A `PipelineError` from the pipeline gives 502 with `error` "pipeline", the failing stage, and the detail. `test_a_pipeline_error_gives_502_with_the_stage` (`tests/test_api.py`)
S18. For any text, `_scrub` leaves no occurrence of the key in it (keys here start with `sk-`, so the replacement text cannot contain one). `test_scrub_removes_every_occurrence_of_the_key` (`tests/test_api.py`)

## Retrieval eval baseline (`evals/retrieval_eval.py`, `evals/embedding_cache.py`)

The baseline cuts each file into fixed windows of characters. Hypothesis builds short texts from the letters a and b and newlines, with small window sizes and overlaps, so one text gives many windows and many line breaks.

R1. Every character of the text lies in at least one window. `test_every_character_is_in_a_window` (`tests/test_retrieval_eval.py`)
R2. No window is empty or longer than the window size. `test_no_window_is_empty_or_longer_than_the_size` (`tests/test_retrieval_eval.py`)
R3. Each window overlaps the next by exactly the overlap, and ends later than the one before, so the last window is never a copy of the tail of the one before it. `test_consecutive_windows_overlap_by_exactly_the_overlap` (`tests/test_retrieval_eval.py`)
R4. A window's line range is exactly the lines its characters touch, where a newline belongs to the line it ends. `test_the_line_range_is_the_lines_the_characters_touch` (`tests/test_retrieval_eval.py`)
R5. In the real corpus, every baseline chunk has a unique ID, its text lies inside the file lines it names (counted as the parser counts them), and it carries the drug and source the parser gave that file, with no section and no heading path. `test_baseline_chunks_sit_on_the_parsers_lines_and_keep_its_labels` (`tests/test_retrieval_eval.py`)
R6. For any list of texts, the caching embedder returns the same rows as the embedder it wraps, in input order, and sends each distinct text to the wrapped embedder once, so a second call sends nothing. `test_the_cache_returns_the_wrapped_rows_and_sends_each_text_once` (`tests/test_retrieval_eval.py`)
R7. Vectors stored under one model name are never used for another model name. `test_a_different_model_does_not_reuse_stored_vectors` (`tests/test_retrieval_eval.py`)

## Corpus parser (`load_corpus`)

Hypothesis builds small synthetic documents (a title, an optional source line, headings at levels 2 to 5, blocks of lines, some very long) and checks these on each.

14. Every line that is not blank, not a heading, and not the title or source line lies in exactly one chunk, so no text is lost or repeated. `test_every_body_line_is_in_exactly_one_chunk` (`tests/test_corpus.py`)
15. A chunk's `text` is exactly the file's lines from `line_start` to `line_end` joined with newlines, and its `id` is `<file>#L<start>-<end>`, so a quote can be checked against the file. `test_text_is_the_files_lines_verbatim` (`tests/test_corpus.py`)
16. Chunks come in file order, never overlap, and have unique IDs. `test_chunks_are_ordered_disjoint_and_uniquely_named` (`tests/test_corpus.py`)
17. No chunk is longer than 5,000 characters unless it is a single line. `test_chunks_respect_the_size_cap_unless_one_line` (`tests/test_corpus.py`)
18. No chunk contains a heading line, and every chunk starts and ends on a non-blank line. `test_no_chunk_contains_a_heading_or_blank_edge` (`tests/test_corpus.py`)
19. A chunk's `heading_path` is the stack of headings above its text: a heading replaces the headings at its own level and deeper. `test_heading_path_is_the_heading_stack` (`tests/test_corpus.py`)
20. Parsing the same directory twice gives equal results. `test_parsing_twice_gives_the_same_chunks` (`tests/test_corpus.py`)
21. A file name that is not `dailymed-<drug>`, `medlineplus-<drug>` or `GLOSSARY` raises an error that names the file. `test_unknown_file_name_is_rejected_by_name` (`tests/test_corpus.py`)
22. In the real corpus, a run of consecutive lines holding a ` | ` table is never split across chunks. `test_no_table_block_is_split` (`tests/test_corpus.py`)
23. In the real corpus, every top-level heading maps to a section key, or is on a short list in the test of headings left unmapped on purpose. `test_every_top_level_heading_is_mapped_or_listed` (`tests/test_corpus.py`)
24. No chunk text carries a carriage return, although `GLOSSARY.md` uses Windows line ends. `test_no_chunk_text_carries_a_carriage_return` (`tests/test_corpus.py`)

## Tools (`tools.py`)

The tools tests run on the real corpus with a fake embedder, so they need no network. Hypothesis varies the drug, the letter case and the arbitrary text.

T1. For every drug, source and section that exists in the corpus, `get_section` returns exactly the corpus passages with that drug, source and section, in file order, no more and no fewer. `test_get_section_returns_exactly_the_matching_chunks_in_file_order` (`tests/test_tools.py`)
T2. Every passage `find_interactions` returns contains, ignoring letter case, every term it lists as matched, and lists at least one. `test_every_interaction_passage_contains_a_term_it_reports` (`tests/test_tools.py`)
T3. `find_interactions(a, b)` and `find_interactions(b, a)` return the same set of passages, for every pair of drugs in the corpus. `test_interactions_are_the_same_in_both_argument_orders` (`tests/test_tools.py`)
T4. Whatever text the model gives as a drug, source, section, search query or glossary term, no tool raises. For a text that is not a drug in the corpus, `get_section` and `search_corpus` return no passages and a note that names every drug in the corpus, and `find_interactions` says the corpus has no document for it. `test_no_tool_raises_and_an_unknown_drug_names_the_corpus_drugs` (`tests/test_tools.py`)
T5. A source or section that does not exist makes `search_corpus` return no passages and a note that lists every valid source or section. `test_unknown_source_or_section_in_search_gives_no_passages_and_lists_valid_ones` (`tests/test_tools.py`)
T6. `resolve_drug` maps every generic name, and every brand name read from the corpus, to its generic name, in any letter case and with spaces or tabs around it. `test_resolve_drug_maps_each_generic_name_in_any_case`, `test_resolve_drug_maps_each_brand_name_in_any_case` (`tests/test_tools.py`)
T7. Every glossary entry is found by its own full term, in any letter case. `test_every_glossary_entry_is_found_by_its_own_term` (`tests/test_tools.py`)
T8. Examples on the real corpus: warfarin contraindications, Eliquis resolving to apixaban, and aspirin having no contraindications section but a `warnings` one (`test_get_section_examples`); warfarin with sertraline, with ibuprofen, and apixaban with ibuprofen through the class term "NSAID" (`test_warfarin_and_sertraline_find_each_other`, `test_warfarin_and_ibuprofen_find_the_warfarin_type_anticoagulants_passage`, `test_apixaban_and_ibuprofen_match_through_the_class_term`); a drug missing from the corpus (`test_a_drug_missing_from_the_corpus_is_named_in_the_note`); glossary lookups by "INR" and lower-case "ssri" (`test_glossary_lookups`); a search filtered by the brand name Zoloft returns only sertraline (`test_search_by_brand_name_returns_only_that_drug`) (`tests/test_tools.py`)

## Grounding and pipeline (`grounding.py`, `pipeline.py`)

The grounding tests draw spans from the real corpus passages. The pipeline tests run the real corpus and tools with a fake embedder and scripted `FunctionModel`s, so they need no network.

25. Any contiguous span of a passage passes the quote check, also after its whitespace is reflowed and its case changed. `test_any_span_of_a_passage_passes_after_reflow_and_case_change` (`tests/test_grounding.py`)
26. A quote that contains a token absent from the passage fails the quote check. `test_a_quote_with_a_token_absent_from_the_passage_fails` (`tests/test_grounding.py`)
27. `markers` returns exactly the numbers written into a prose, in order, for `[1][2]` and `[1, 2]` alike. `test_markers_returns_the_numbers_written_into_the_prose_in_order` (`tests/test_grounding.py`)
28. After `drop_dangling`, no dangling marker remains and every sentence without one is still present. `test_drop_dangling_leaves_no_dangling_marker_and_keeps_every_clean_sentence` (`tests/test_grounding.py`)
29. A claim with no citation, a citation to a passage no tool returned, or a quote that is not in the cited passage fails; a claim that passes is absent from the result. `test_failed_claims_names_each_kind_of_failure` (`tests/test_grounding.py`)
30. A supported claim shows up in `sources` and in a `Sources:` line, and `answer` ends with the disclaimer. `test_happy_path_cites_the_file_and_ends_with_the_disclaimer` (`tests/test_pipeline.py`)
31. A claim with a planted quote is marked unsupported by the quote check even when the critic calls it supported; after one retry it is redacted, listed under `critic.removed`, and its file is left out of `sources`. `test_a_planted_quote_is_caught_without_the_critic_and_redacted_after_one_retry` (`tests/test_pipeline.py`)
32. When the retry fixes an unsupported verdict, one follow-up worker runs and the writer is not called for a redaction. `test_a_follow_up_that_the_retry_fixes_needs_no_redaction` (`tests/test_pipeline.py`)
33. An out-of-scope question calls no worker, writer, or critic and gets a refusal that ends with the disclaimer. `test_an_out_of_scope_question_gets_a_refusal_and_calls_nobody_else` (`tests/test_pipeline.py`)
34. A worker that asks for more than `MAX_TOOL_CALLS` tool calls gets the budget message, runs no more than `MAX_TOOL_CALLS`, and still returns findings. `test_a_worker_over_its_tool_budget_gets_the_budget_message_and_still_returns_findings` (`tests/test_pipeline.py`)
35. A redaction that leaves a dangling marker ends with `marker_check` `repaired` and no dangling marker in the answer. `test_a_dangling_marker_left_by_the_redaction_is_repaired` (`tests/test_pipeline.py`)
36. One worker that raises does not fail the request; its error reaches the writer as `not_found`. `test_one_failed_worker_does_not_fail_the_request` (`tests/test_pipeline.py`)
37. When every worker raises, the request fails at the research stage and the writer is never called, so an outage is not reported as a gap in the documents. `test_the_request_fails_when_every_worker_fails` (`tests/test_pipeline.py`)
