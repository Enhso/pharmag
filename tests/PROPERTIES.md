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

## Server and page

7. The server starts and `GET /health` answers 200 whether the configuration is valid, defective or entirely absent. `test_health_is_ok_with_valid_config`, `test_health_is_degraded_but_200_with_invalid_config`, `test_server_starts_with_no_configuration_at_all` (`tests/test_api.py`)
8. With valid configuration, `POST /ask` with a non-empty question answers 200 with a placeholder answer, no sources, and the code-set not-medical-advice sentence. `test_ask_returns_the_placeholder_with_valid_config` (`tests/test_api.py`)
9. With defective configuration, `POST /ask` answers 503 and names each bad variable. `test_ask_is_503_and_names_the_bad_variables_with_invalid_config` (`tests/test_api.py`)
10. A body without a non-empty string `question` gets 422, whatever the configuration. `test_ask_rejects_a_malformed_body_with_422` (`tests/test_api.py`)
11. The API key value never appears in `/health` or `/ask` responses, including when the key is defective. `test_health_is_degraded_but_200_with_invalid_config`, `test_ask_is_503_and_names_the_bad_variables_with_invalid_config` (`tests/test_api.py`)
12. No file in the static folder refers to another host. `test_the_page_loads_nothing_from_another_host` (`tests/test_api.py`)
13. `GET /` serves the page and its CSS and JavaScript from the same server. `test_root_serves_the_page_and_its_assets` (`tests/test_api.py`)

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
