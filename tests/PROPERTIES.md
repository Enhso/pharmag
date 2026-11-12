# Properties

Each line says what must hold for every input of a kind, and names the test that checks it.
Hypothesis runs the config tests on many generated environments, so one line covers many cases.

## Config check (`load_settings`)

1. For any environment, the check reports exactly the required variables that are missing, empty, padded with whitespace, wrapped in a quote, or (for the base URL) lacking `http://` or `https://`. It lists each at most once, in the fixed order API key, base URL, model, embedding model, and it ignores every other variable. `test_reports_exactly_the_defective_variables` (`tests/test_config.py`)
2. When every required variable is fine, the check returns the settings with the values exactly as given. It never trims, unquotes or otherwise repairs a value. `test_reports_exactly_the_defective_variables` (`tests/test_config.py`)
3. For any environment, no problem (variable name or text) contains any variable's value, so a bad value cannot leak through a response or a log. `test_no_problem_contains_a_value` (`tests/test_config.py`)
4. Printing the settings does not show the API key. `test_the_printed_settings_hide_the_key` (`tests/test_config.py`)
5. When a required variable is missing and the environment holds an `OPENAI_*` name that is the real name with one character deleted, the problem text names that near-miss. `test_a_misspelled_name_is_named_when_the_real_one_is_missing` (`tests/test_config.py`)
6. An unrelated `OPENAI_*` variable, or another required variable, is never offered as a misspelling. `test_other_openai_names_are_not_taken_for_misspellings` (`tests/test_config.py`)

## Search index (Index.search)

The index tests use a fake embedder that hashes words into 32 numbers, so they need no network. Hypothesis builds many random chunk lists and queries.

I1. Every returned chunk matches every filter given (`drug`, `source`, `section`). `test_every_hit_satisfies_every_filter` (`tests/test_index.py`)
I2. A search returns at most `k` hits, never the same chunk twice, and the scores never go up from one hit to the next. `test_at_most_k_distinct_hits_in_non_increasing_score_order` (`tests/test_index.py`)
I3. A chunk ranked first by the vector comparison and first by the keyword (BM25) ranking is the first result. `test_first_in_both_rankings_is_first_overall` (`tests/test_index.py`)
I4. Searching with a chunk's own embedding text returns that chunk first, when no other chunk has the same vector. `test_searching_a_chunks_own_text_returns_it_first` (`tests/test_index.py`)
I5. Every stored embedding has length 1, so a dot product equals cosine similarity. `test_stored_rows_have_unit_length` (`tests/test_index.py`)
I6. `OpenAIEmbedder.embed` returns one row per text in input order, for any number of texts, batch size and concurrency, even when the server answers batches or rows out of order, and never sends a batch larger than the batch size. `test_openai_embedder_keeps_input_order` (`tests/test_index.py`)
I7. Building twice from the same chunks and searching gives identical results. `test_building_twice_gives_equal_results` (`tests/test_index.py`)
I8. Examples: a rare exact token ("CYP3A4") puts its one chunk first even when the vector ranking is no help (`test_a_rare_exact_token_wins_even_when_dense_does_not_help`); a drug filter drops other drugs (`test_a_drug_filter_excludes_other_drugs`); no matching candidates gives an empty list (`test_no_candidates_gives_an_empty_list`); a query sharing no word with a chunk gives it no keyword rank (`test_a_query_with_no_lexical_overlap_has_no_bm25_rank`) (`tests/test_index.py`)

## Server and page

7. The server starts and `GET /health` answers 200 whether the configuration is valid, defective or entirely absent. `test_health_is_ok_with_valid_config`, `test_health_is_degraded_but_200_with_invalid_config`, `test_server_starts_with_no_configuration_at_all` (`tests/test_api.py`)
8. With valid configuration, `POST /ask` with a non-empty question answers 200 with a placeholder answer, no sources, and the code-set not-medical-advice sentence. `test_ask_returns_the_placeholder_with_valid_config` (`tests/test_api.py`)
9. With defective configuration, `POST /ask` answers 503 and names each bad variable. `test_ask_is_503_and_names_the_bad_variables_with_invalid_config` (`tests/test_api.py`)
10. A body without a non-empty string `question` gets 422, whatever the configuration. `test_ask_rejects_a_malformed_body_with_422` (`tests/test_api.py`)
11. The API key value never appears in `/health` or `/ask` responses, including when the key is defective. `test_health_is_degraded_but_200_with_invalid_config`, `test_ask_is_503_and_names_the_bad_variables_with_invalid_config` (`tests/test_api.py`)
12. No file in the static folder refers to another host. `test_the_page_loads_nothing_from_another_host` (`tests/test_api.py`)
13. `GET /` serves the page and its CSS and JavaScript from the same server. `test_root_serves_the_page_and_its_assets` (`tests/test_api.py`)

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
