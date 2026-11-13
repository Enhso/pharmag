"""Ask the eval questions against a running server and compare the sources with the expected ones.

usage: live_check.py BASE_URL OUT_DIR [ID ...]
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

base, out_dir, wanted = sys.argv[1], Path(sys.argv[2]), set(sys.argv[3:])
out_dir.mkdir(parents=True, exist_ok=True)
questions = json.loads(Path("evals/questions.json").read_text())["questions"]

rows = []
for q in questions:
    if wanted and q["id"] not in wanted:
        continue
    request = urllib.request.Request(
        f"{base}/ask",
        data=json.dumps({"question": q["question"]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            status, body = response.status, json.load(response)
    except urllib.error.HTTPError as error:
        status, body = error.code, json.loads(error.read() or b"{}")
    seconds = time.monotonic() - started
    (out_dir / f"{q['id']}.json").write_text(json.dumps(body, indent=1))

    expected, allowed = set(q["expected_sources"]), set(q.get("allowed_sources", []))
    got = set(body.get("sources", []))
    critic = body.get("critic", {})
    usage = body.get("usage", {})
    rows.append(
        {
            "id": q["id"],
            "status": status,
            "seconds": round(seconds, 1),
            "missing": sorted(expected - got),
            "extra": sorted(got - expected - allowed),
            "claims": len(critic.get("verdicts", [])),
            "removed": len(critic.get("removed", [])),
            "cautions": len(critic.get("cautions", [])),
            "rounds": critic.get("review_rounds"),
            "tools": sorted({c["tool"] for c in body.get("tool_calls", [])}),
            "in_tok": usage.get("input_tokens"),
            "cached": usage.get("cached_input_tokens"),
            "out_tok": usage.get("output_tokens"),
            "error": body.get("error"),
        }
    )
    print(json.dumps(rows[-1]), flush=True)

(out_dir / "summary.json").write_text(json.dumps(rows, indent=1))
ok = [r for r in rows if r["status"] == 200 and not r["missing"]]
print(f"{len(ok)}/{len(rows)} answered with every expected source")
