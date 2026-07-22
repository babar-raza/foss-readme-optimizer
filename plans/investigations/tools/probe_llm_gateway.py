# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Live characterization of the llm.professionalize.com gateway.

Probes (read/inference only, no state mutation anywhere):
  1. GET  /models                      -> model inventory
  2. POST /chat/completions            -> context-window practical limit (size ladder)
  3. POST /chat/completions            -> structured-output reliability (N trials/model)
  4. POST /embeddings                  -> similarity usefulness on known README pairs
  5. POST /chat/completions w/ tools   -> native tool-calling, single step (sprint Task 10)
  6. POST /chat/completions w/ tools   -> multi-step tool use (tool call -> tool result -> reply)
  7. POST /chat/completions w/ tools   -> parallel tool-call reliability
Secrets are never printed; output JSON passes through the project's redaction module.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
from readme_agent import env  # noqa: E402  (reuse proven precedence + secret list)
from readme_agent.evidence.redaction import redact  # noqa: E402

BASE = env.llm_base_url().rstrip("/")
KEY = env.llm_api_key()
HDRS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
TIMEOUT = 60

OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "llm-probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FIXTURES = REPO_ROOT / "tests" / "fixtures" / "readmes" / "real_audit_2026-07-17"

results: dict = {"base_url_host": BASE.split("//")[-1].split("/")[0], "probes": {}}


def chat(model: str, content: str, max_tokens: int = 200) -> tuple[bool, str, float, dict]:
    t0 = time.time()
    try:
        r = requests.post(
            f"{BASE}/chat/completions",
            headers=HDRS,
            json={
                "model": model,
                "messages": [{"role": "user", "content": content}],
                "temperature": 0.0,
                "max_tokens": max_tokens,
            },
            timeout=TIMEOUT,
        )
        dt = time.time() - t0
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}", dt, {}
        d = r.json()
        return True, d["choices"][0]["message"]["content"] or "", dt, d.get("usage", {})
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}", time.time() - t0, {}


def chat_raw(
    model: str, messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 250
) -> tuple[bool, dict, float, dict]:
    """Like chat(), but returns the raw response `message` dict (for tool_calls) not just
    text, plus the response's own `usage` dict (added alongside the multi-turn
    conversation-growth probe below -- the model-reported `prompt_tokens` per turn is the
    ground truth for how a real, growing planner conversation's token cost actually
    accumulates, not a client-side tokenizer estimate)."""
    t0 = time.time()
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    try:
        r = requests.post(f"{BASE}/chat/completions", headers=HDRS, json=payload, timeout=TIMEOUT)
        dt = time.time() - t0
        if r.status_code != 200:
            return False, {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, dt, {}
        d = r.json()
        return True, d["choices"][0]["message"], dt, d.get("usage", {})
    except Exception as e:  # noqa: BLE001
        return False, {"error": f"{type(e).__name__}: {e}"}, time.time() - t0, {}


TOOL_LOOKUP_LICENSE = {
    "type": "function",
    "function": {
        "name": "get_repository_license",
        "description": "Look up the detected license identifier for a GitHub repository.",
        "parameters": {
            "type": "object",
            "properties": {"org_repo": {"type": "string", "description": "'org/repo' identifier"}},
            "required": ["org_repo"],
        },
    },
}
TOOL_COUNT_GAPS = {
    "type": "function",
    "function": {
        "name": "count_readme_gaps",
        "description": "Count how many required presentation elements are missing from a README.",
        "parameters": {
            "type": "object",
            "properties": {"org_repo": {"type": "string", "description": "'org/repo' identifier"}},
            "required": ["org_repo"],
        },
    },
}


def _extract_tool_calls(message: dict) -> list[dict]:
    calls = message.get("tool_calls") or []
    valid = []
    for c in calls:
        fn = c.get("function", {})
        name = fn.get("name")
        args_raw = fn.get("arguments")
        args_ok = False
        if isinstance(args_raw, str):
            try:
                json.loads(args_raw)
                args_ok = True
            except Exception:  # noqa: BLE001
                args_ok = False
        valid.append({"name": name, "args_valid_json": args_ok, "has_id": bool(c.get("id"))})
    return valid


# --- 1. model inventory -----------------------------------------------------
try:
    r = requests.get(f"{BASE}/models", headers=HDRS, timeout=TIMEOUT)
    models = [m["id"] for m in r.json().get("data", [])] if r.status_code == 200 else []
    results["probes"]["models"] = {"status": r.status_code, "ids": models}
except Exception as e:  # noqa: BLE001
    results["probes"]["models"] = {"error": str(e)}
    models = []
print(f"[1] models: {results['probes']['models']}")

chat_models = [
    m for m in models if any(s in m.lower() for s in ("gpt", "qwen")) and "embed" not in m.lower()
]
embed_models = [m for m in models if "embed" in m.lower()]

# --- 2. context-window ladder ----------------------------------------------
# Filler ~4 chars/token. Ask for a needle at the END to prove full-prompt visibility.
# BUGFIX (2026-07-21): the previous version built `filler` from a FIXED-length
# (~5,600-char) string ("lorem ipsum dolor sit amet " * 200) and then sliced it
# to `approx_tok * 4 - 400` chars -- but slicing past a string's actual length
# is a Python no-op, so every ladder rung from 2,000 to 96,000 "approx tokens"
# silently sent the same ~5,600-char (~1,400-token) filler. This exactly
# explained why `probe-results.json`'s own `usage.prompt_tokens` stayed flat
# (~1,031-1,032) across the whole ladder in the prior run -- not a gateway
# quirk, a one-line bug. Fixed by scaling the repeat count to the target size
# BEFORE slicing.
_FILLER_UNIT = "lorem ipsum dolor sit amet "
ladder = [2_000, 8_000, 16_000, 32_000, 64_000, 96_000]  # approx tokens
ctx: dict = {}
for model in chat_models:
    ctx[model] = []
    for approx_tok in ladder:
        target_chars = approx_tok * 4 - 400
        repeats = target_chars // len(_FILLER_UNIT) + 1
        filler = (_FILLER_UNIT * repeats)[:target_chars]
        prompt = (
            f"{filler}\n\nIMPORTANT: reply with exactly the code word: ZEBRA-{approx_tok}."
            " Nothing else."
        )
        ok, out, dt, usage = chat(model, prompt, max_tokens=30)
        found = f"ZEBRA-{approx_tok}" in out
        ctx[model].append(
            {
                "approx_tokens": approx_tok,
                "ok": ok,
                "needle_found": found,
                "latency_s": round(dt, 1),
                "prompt_tokens": usage.get("prompt_tokens"),
                "note": None if ok else out[:150],
            }
        )
        print(f"[2] {model} @~{approx_tok}tok: ok={ok} needle={found} {dt:.1f}s")
        if not ok:
            break  # ladder stops at first hard failure
results["probes"]["context_ladder"] = ctx

# --- 2b. multi-turn conversation growth (real planner shape, not a flat prompt) ----
# `AGT-007`/`LLM-019`: the production consumer of a context budget is
# `supervisor/loop.py`'s growing tool-calling conversation (system prompt +
# initial dossier, then an appended assistant tool_call + tool result pair
# each turn, up to `DEFAULT_MAX_TURNS=8`), not a single flat prompt. The
# context-ladder probe above answers "how large a single prompt survives" --
# it does not answer "how large does a real 7-turn planner conversation
# actually get." This section measures that directly via the gateway's own
# `usage.prompt_tokens` at each turn, so a dossier token budget can be sized
# against real accumulation, not a guess.
_DOSSIER_SYSTEM = (
    "You are an autonomous repository-presentation planner. You have a menu of "
    "capabilities describing what each one observes or changes. Given the current "
    "observation, call exactly one capability per turn that would most usefully extend "
    "your understanding of the repository, or address a gap you've observed. Once you "
    "have enough information and no further capability would help, stop calling tools "
    "and explain why in plain text."
)
# A moderately realistic initial dossier -- bootstrap result + 9 specialist summaries,
# sized like a real (not synthetic-filler) planner turn-0 payload.
_DOSSIER_USER = (
    "Repository: acme/widget. Initial observation: "
    '{"has_readme": true, "has_license_file": true, "readme_length_chars": 4820, '
    '"manifest_keys": ["pom.xml"]}. Specialist observations: '
    '{"readme_reconciliation": "CHANGED", "github_generated_surface_audit": "CHANGED", '
    '"package_release_audit": "NO_CHANGE", "metadata_presentation": "NO_CHANGE", '
    '"community_files_presentation": "NO_CHANGE", "cross_surface_validation": "NO_CHANGE", '
    '"readme_presentation": "CHANGED", "visual_preparation": "NO_CHANGE", '
    '"independent_verification": "NO_CHANGE"}. Independent verification findings: '
    '{"evidence_completeness": {"community_files_presentation": "incomplete"}, '
    '"requirement_map": {"readme_presentation": ["RDM-008"]}, "adversarial_findings": [], '
    '"failure_escalations": {}}. Plan the next step, or stop if nothing further would help."'
)
MULTI_TURN_MAX_TURNS = 8  # matches supervisor/loop.py::DEFAULT_MAX_TURNS
multi_turn_growth: dict = {}
for model in chat_models:
    messages: list[dict] = [
        {"role": "system", "content": _DOSSIER_SYSTEM},
        {"role": "user", "content": _DOSSIER_USER},
    ]
    turns: list[dict] = []
    for turn in range(1, MULTI_TURN_MAX_TURNS + 1):
        ok, msg, dt, usage = chat_raw(
            model, messages, tools=[TOOL_LOOKUP_LICENSE, TOOL_COUNT_GAPS], max_tokens=300
        )
        calls = _extract_tool_calls(msg) if ok else []
        turns.append(
            {
                "turn": turn,
                "ok": ok,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "n_tool_calls": len(calls),
                "latency_s": round(dt, 1),
            }
        )
        print(
            f"[2b] {model} turn {turn}/{MULTI_TURN_MAX_TURNS}: ok={ok} "
            f"prompt_tokens={usage.get('prompt_tokens')} tool_calls={len(calls)} {dt:.1f}s"
        )
        if not ok or not calls:
            break  # model stopped calling tools (or errored) -- real convergence, stop growing
        raw_calls = msg.get("tool_calls") or []
        messages.append(
            {"role": "assistant", "content": msg.get("content"), "tool_calls": raw_calls}
        )
        for c in raw_calls:
            fn_name = c.get("function", {}).get("name", "")
            synthetic_result = (
                {"license": "MIT"} if fn_name == "get_repository_license" else {"gap_count": 2}
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": c.get("id", ""),
                    "content": json.dumps(synthetic_result),
                }
            )
    multi_turn_growth[model] = {"turns": turns}
results["probes"]["multi_turn_conversation_growth"] = multi_turn_growth

# --- 3. structured-output reliability ---------------------------------------
SCHEMA_PROMPT = (
    "Return ONLY a JSON object (no prose, no code fences) with exactly these keys: "
    '"product" (string), "capabilities" (array of exactly 3 short strings), '
    '"install_verified" (boolean), "confidence" (number 0..1). '
    "Describe a fictional Java Excel library called AcmeCells."
)


def try_parse(txt: str) -> tuple[bool, str]:
    t = txt.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0] if "```" in t else t
    try:
        d = json.loads(t)
    except Exception as e:  # noqa: BLE001
        return False, f"json:{e}"
    ok = (
        isinstance(d.get("product"), str)
        and isinstance(d.get("capabilities"), list)
        and len(d.get("capabilities", [])) == 3
        and isinstance(d.get("install_verified"), bool)
        and isinstance(d.get("confidence"), (int, float))
    )
    return ok, "schema-ok" if ok else "schema-mismatch"


structured: dict = {}
trials_per = {m: (10 if "gpt" in m.lower() else 5) for m in chat_models}
for model in chat_models:
    n = trials_per[model]
    outcomes = []
    for i in range(n):
        ok, out, dt, _ = chat(model, SCHEMA_PROMPT, max_tokens=250)
        parsed, why = try_parse(out) if ok else (False, out[:100])
        fenced = ok and out.strip().startswith("```")
        outcomes.append(
            {"ok": ok, "valid": parsed, "why": why, "fenced": fenced, "latency_s": round(dt, 1)}
        )
        print(f"[3] {model} trial {i + 1}/{n}: valid={parsed} ({why}) fenced={fenced} {dt:.1f}s")
    structured[model] = {
        "trials": n,
        "valid_rate": sum(o["valid"] for o in outcomes) / n,
        "fenced_rate": sum(o["fenced"] for o in outcomes) / n,
        "outcomes": outcomes,
    }
results["probes"]["structured_output"] = structured


# --- 4. embeddings similarity ------------------------------------------------
def embed(model: str, texts: list[str]) -> list[list[float]] | str:
    try:
        r = requests.post(
            f"{BASE}/embeddings",
            headers=HDRS,
            json={"model": model, "input": texts},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return f"HTTP {r.status_code}: {r.text[:200]}"
        return [d["embedding"] for d in r.json()["data"]]
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"


def cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


emb_result: dict = {}
pair_files = {"3d-java": None, "3d-python": None, "cells-java": None, "words-python": None}
for name in pair_files:
    p = FIXTURES / f"{name}.md"
    pair_files[name] = p.read_text(encoding="utf-8")[:2000] if p.exists() else None
if embed_models and all(pair_files.values()):
    em = embed_models[0]
    vecs = embed(em, list(pair_files.values()))
    if isinstance(vecs, list):
        names = list(pair_files)
        sims = {
            f"{a}~{b}": round(cos(vecs[i], vecs[j]), 4)
            for i, a in enumerate(names)
            for j, b in enumerate(names)
            if i < j
        }
        emb_result = {
            "model": em,
            "dims": len(vecs[0]),
            "cosine": sims,
            "control_expectation": "3d-java~3d-python (same bot template) must be highest",
        }
        print(f"[4] embeddings {em} dims={len(vecs[0])}: {sims}")
    else:
        emb_result = {"model": em, "error": vecs}
        print(f"[4] embeddings error: {vecs}")
else:
    emb_result = {"skipped": f"embed_models={embed_models}, fixtures_ok={all(pair_files.values())}"}
results["probes"]["embeddings"] = emb_result

# --- 5. native tool-calling, single step -------------------------------------
TOOL_PROMPT = (
    "What license does the repository 'acme/widget' use? Use the available tool to find out, "
    "do not guess."
)
tool_calling: dict = {}
for model in chat_models:
    n = 5
    outcomes = []
    for i in range(n):
        ok, msg, dt, _usage = chat_raw(
            model,
            [{"role": "user", "content": TOOL_PROMPT}],
            tools=[TOOL_LOOKUP_LICENSE, TOOL_COUNT_GAPS],
        )
        calls = _extract_tool_calls(msg) if ok else []
        called_right_tool = any(
            c["name"] == "get_repository_license" and c["args_valid_json"] for c in calls
        )
        outcomes.append(
            {
                "ok": ok,
                "n_tool_calls": len(calls),
                "called_right_tool": called_right_tool,
                "fell_back_to_text": ok and not calls and bool(msg.get("content")),
                "latency_s": round(dt, 1),
            }
        )
        print(
            f"[5] {model} trial {i + 1}/{n}: ok={ok} tool_calls={len(calls)} "
            f"right_tool={called_right_tool} {dt:.1f}s"
        )
    tool_calling[model] = {
        "trials": n,
        "success_rate": sum(o["called_right_tool"] for o in outcomes) / n,
        "outcomes": outcomes,
    }
results["probes"]["tool_calling_single_step"] = tool_calling

# --- 6. multi-step tool use ---------------------------------------------------
multi_step: dict = {}
for model in chat_models:
    ok1, msg1, dt1, _usage1 = chat_raw(
        model,
        [{"role": "user", "content": TOOL_PROMPT}],
        tools=[TOOL_LOOKUP_LICENSE, TOOL_COUNT_GAPS],
    )
    calls1 = _extract_tool_calls(msg1) if ok1 else []
    if not (ok1 and calls1):
        multi_step[model] = {"round1_ok": ok1, "round1_tool_calls": len(calls1), "skipped": True}
        print(f"[6] {model}: round1 produced no tool call, skipping round 2")
        continue
    raw_calls = msg1.get("tool_calls") or []
    followup_messages = [
        {"role": "user", "content": TOOL_PROMPT},
        {"role": "assistant", "content": msg1.get("content"), "tool_calls": raw_calls},
    ]
    for c in raw_calls:
        followup_messages.append(
            {
                "role": "tool",
                "tool_call_id": c.get("id", ""),
                "content": json.dumps({"license": "MIT"}),
            }
        )
    ok2, msg2, dt2, _usage2 = chat_raw(
        model, followup_messages, tools=[TOOL_LOOKUP_LICENSE, TOOL_COUNT_GAPS]
    )
    calls2 = _extract_tool_calls(msg2) if ok2 else []
    produced_final_answer = ok2 and bool(msg2.get("content")) and not calls2
    multi_step[model] = {
        "round1_tool_calls": len(calls1),
        "round2_ok": ok2,
        "round2_tool_calls": len(calls2),
        "round2_produced_final_answer": produced_final_answer,
        "round2_latency_s": round(dt2, 1),
    }
    print(
        f"[6] {model}: round2 ok={ok2} tool_calls={len(calls2)} "
        f"final_answer={produced_final_answer} {dt2:.1f}s"
    )
results["probes"]["tool_calling_multi_step"] = multi_step

# --- 7. parallel tool-call reliability ----------------------------------------
PARALLEL_PROMPT = (
    "For the repository 'acme/widget': (1) look up its license, and (2) count its README gaps. "
    "Use the two available tools to answer both parts."
)
parallel: dict = {}
for model in chat_models:
    ok, msg, dt, _usage = chat_raw(
        model,
        [{"role": "user", "content": PARALLEL_PROMPT}],
        tools=[TOOL_LOOKUP_LICENSE, TOOL_COUNT_GAPS],
    )
    calls = _extract_tool_calls(msg) if ok else []
    names = {c["name"] for c in calls}
    both_in_one_response = (
        len(calls) >= 2
        and {
            "get_repository_license",
            "count_readme_gaps",
        }
        <= names
    )
    parallel[model] = {
        "ok": ok,
        "n_tool_calls": len(calls),
        "distinct_tools_called": sorted(names),
        "both_in_one_response": both_in_one_response,
        "latency_s": round(dt, 1),
    }
    print(
        f"[7] {model}: ok={ok} tool_calls={len(calls)} tools={sorted(names)} "
        f"parallel={both_in_one_response} {dt:.1f}s"
    )
results["probes"]["tool_calling_parallel"] = parallel

# --- write redacted evidence -------------------------------------------------
raw = json.dumps(results, indent=2)
(OUT_DIR / "probe-results.json").write_text(redact(raw), encoding="utf-8")
print(f"\nwrote: {(OUT_DIR / 'probe-results.json').relative_to(REPO_ROOT)}")
