from hypothesis import given
from hypothesis import strategies as st

from pharmag.config import (
    API_KEY,
    BASE_URL,
    EMBEDDING_MODEL,
    MODEL,
    REQUIRED,
    ConfigProblem,
    Settings,
    load_settings,
)

# Every value in these tests contains this token, so a test can tell whether a value leaked.
SENTINEL = "k3y-SENTINEL"
ALNUM = st.sampled_from("abcXYZ019")

# Starts and ends with a letter or digit, so it has no edge whitespace or quote. Anything inside.
good_core = st.builds("{}{}{}{}{}".format, ALNUM, st.text(), st.just(SENTINEL), st.text(), ALNUM)

# Variable names outside the four required ones, so they never decide the outcome.
extras = st.dictionaries(st.text(min_size=1), st.text()).map(
    lambda d: {k: v for k, v in d.items() if k not in REQUIRED}
)

KINDS = ("valid", "missing", "empty", "padded", "quoted")


@st.composite
def variable(draw, name):
    """Draw (kind, value) for one required variable; value is None when it is missing."""
    kinds = KINDS + ("no_scheme",) if name == BASE_URL else KINDS
    kind = draw(st.sampled_from(kinds))
    core = draw(good_core)
    good = "https://" + core if name == BASE_URL else core
    pad = draw(st.sampled_from([" ", "\t", "\n"]))
    quote = draw(st.sampled_from(["'", '"']))
    value = {
        "valid": good,
        "missing": None,
        "empty": "",
        "padded": draw(st.sampled_from([pad + good, good + pad, pad + good + pad])),
        "quoted": draw(st.sampled_from([quote + good, good + quote, quote + good + quote])),
        "no_scheme": "ftp://" + core,
    }[kind]
    return kind, value


@st.composite
def environments(draw):
    """An environment plus the kind chosen for each required variable."""
    chosen = {name: draw(variable(name)) for name in REQUIRED}
    environ = draw(extras)
    environ.update({n: v for n, (_, v) in chosen.items() if v is not None})
    return environ, {n: kind for n, (kind, _) in chosen.items()}


@given(environments())
def test_reports_exactly_the_defective_variables(case):
    environ, kinds = case
    result = load_settings(environ)
    defective = [n for n in REQUIRED if kinds[n] != "valid"]
    if defective:
        assert isinstance(result, list)
        assert [p.variable for p in result] == defective
    else:
        assert result == Settings(
            api_key=environ[API_KEY],
            base_url=environ[BASE_URL],
            model=environ[MODEL],
            embedding_model=environ[EMBEDDING_MODEL],
        )


@given(environments())
def test_no_problem_contains_a_value(case):
    environ, _ = case
    result = load_settings(environ)
    if not isinstance(result, Settings):
        assert SENTINEL not in str(result)


def test_the_printed_settings_hide_the_key():
    settings = Settings(api_key="sk-secret-xyz", base_url="u", model="m", embedding_model="e")
    assert "sk-secret-xyz" not in repr(settings)


@given(
    st.sampled_from(REQUIRED),
    st.data(),
)
def test_a_misspelled_name_is_named_when_the_real_one_is_missing(name, data):
    # Delete one character after the "OPENAI_" prefix.
    at = data.draw(st.integers(len("OPENAI_"), len(name) - 1))
    typo = name[:at] + name[at + 1 :]
    environ = {n: "https://x.example" if n == BASE_URL else "x" for n in REQUIRED if n != name}
    environ[typo] = "x"
    result = load_settings(environ)
    assert isinstance(result, list)
    [problem] = result
    assert problem.variable == name
    assert typo in problem.problem


def test_other_openai_names_are_not_taken_for_misspellings():
    environ = {
        API_KEY: "x",
        BASE_URL: "https://x.example",
        EMBEDDING_MODEL: "x",  # a required name, so never a hint for OPENAI_MODEL
        "OPENAI_ORG_ID": "x",
        "PATH": "/usr/bin",
    }
    assert load_settings(environ) == [ConfigProblem(MODEL, "is not set")]


def test_the_real_defective_file_is_reported_variable_by_variable():
    environ = {
        API_KEY: "'sk-abc'",
        "OPENAI_BASE_UR": "'https://llm.example/v1'",
        MODEL: "'m'",
        EMBEDDING_MODEL: "'e'",
    }
    problems = load_settings(environ)
    assert isinstance(problems, list)
    assert [p.variable for p in problems] == list(REQUIRED)
    assert "OPENAI_BASE_UR" in problems[1].problem
    assert "sk-abc" not in str(problems)
