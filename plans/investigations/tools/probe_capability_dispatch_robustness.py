# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Live robustness campaign against the REAL capability dispatcher (sprint
Task 4.2's production code, src/readme_agent/capabilities/), prompted by an
independent review (2026-07-19): Wave 2's live evidence was N=1 trials,
happy-path only, one model, one tool offered at a time -- not enough to
claim the dispatch layer is reliable under real LLM variability, which is
different from and additional to the synthetic/hand-crafted adversarial
inputs already unit-tested in tests/unit/test_capability_dispatcher.py.

Dimensions probed, all through the real registry + dispatcher, no mocks:
  1. Multi-trial consistency per capability (N=3, qwen3-next, one tool offered)
  2. Full 3-tool menu with an open-ended instruction (does the model pick
     validly and consistently when it has to choose, not just comply?)
  3. An instruction with no good tool match (does the model over-eagerly
     force a tool call, or correctly call none?)
  4. gpt-oss (the shipped engine's *default* model, env.DEFAULT_LLM_MODEL)
     single-tool dispatch -- L6 found it reliable for single-step tool
     calls despite being unreliable for freeform JSON; this checks that
     finding holds through the actual production dispatcher, not just the
     gateway-characterization probe script.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
from readme_agent import env  # noqa: E402
from readme_agent.capabilities import dispatcher, registry  # noqa: E402
from readme_agent.evidence.redaction import redact  # noqa: E402

BASE = env.llm_base_url().rstrip("/")
KEY = env.llm_api_key()
HDRS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
TIMEOUT = 90
ORG_REPO = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"  # allow-listed, mode: dry_run pilot

OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "capability-dispatch-robustness"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {"read_only_local", "read_only_network"}


def plan(model: str, instruction: str, tools: list[dict]) -> tuple[bool, dict, float]:
    t0 = time.time()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": instruction}],
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 200,
    }
    try:
        r = requests.post(f"{BASE}/chat/completions", headers=HDRS, json=payload, timeout=TIMEOUT)
        dt = time.time() - t0
        if r.status_code != 200:
            return False, {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, dt
        return True, r.json()["choices"][0]["message"], dt
    except Exception as e:  # noqa: BLE001
        return False, {"error": f"{type(e).__name__}: {e}"}, time.time() - t0


results: dict = {"org_repo": ORG_REPO, "dimensions": {}}

# --- 1. multi-trial consistency per capability --------------------------------
CAPABILITY_INSTRUCTIONS = {
    "inspect_repository": f"Inspect the repository {ORG_REPO} using the available tool.",
    "detect_readme_gaps": (
        f"Check the README of {ORG_REPO} for presentation gaps using the available tool."
    ),
    "check_install_path": (
        f"Check whether {ORG_REPO} resolves against its package registry using the tool."
    ),
}
dim1: dict = {}
for cap_id, instruction in CAPABILITY_INSTRUCTIONS.items():
    tool = registry.get(cap_id).to_tool_schema()
    trials = []
    for i in range(3):
        ok, msg, dt = plan("qwen3-next", instruction, [tool])
        if not ok:
            trials.append({"ok": False, "error": msg.get("error"), "latency_s": round(dt, 1)})
            print(f"[1] {cap_id} trial {i + 1}/3: request FAILED {msg.get('error')}")
            continue
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            trials.append({"ok": True, "outcome": "no_tool_call", "content": msg.get("content")})
            print(f"[1] {cap_id} trial {i + 1}/3: NO TOOL CALL -- content={msg.get('content')!r}")
            continue
        result = dispatcher.dispatch_tool_call(tool_calls[0], allowed_permissions=ALLOWED)
        trials.append(
            {
                "ok": True,
                "outcome": result.outcome,
                "result": result.result,
                "error": result.error,
                "latency_s": round(dt, 1),
            }
        )
        print(f"[1] {cap_id} trial {i + 1}/3: dispatch outcome={result.outcome} {dt:.1f}s")
    dim1[cap_id] = trials
results["dimensions"]["multi_trial_consistency"] = dim1

# --- 2. full 3-tool menu, open-ended instruction -------------------------------
ALL_TOOLS = registry.all_tool_schemas()
OPEN_ENDED = (
    f"Learn what you can about the repository {ORG_REPO}'s presentation quality. "
    "Use exactly one of the available tools."
)
dim2 = []
for i in range(3):
    ok, msg, dt = plan("qwen3-next", OPEN_ENDED, ALL_TOOLS)
    if not ok:
        dim2.append({"ok": False, "error": msg.get("error")})
        print(f"[2] trial {i + 1}/3: request FAILED {msg.get('error')}")
        continue
    tool_calls = msg.get("tool_calls") or []
    if not tool_calls:
        dim2.append({"ok": True, "outcome": "no_tool_call", "content": msg.get("content")})
        print(f"[2] trial {i + 1}/3: NO TOOL CALL -- content={msg.get('content')!r}")
        continue
    name = tool_calls[0]["function"]["name"]
    valid_choice = registry.get(name) is not None
    result = dispatcher.dispatch_tool_call(tool_calls[0], allowed_permissions=ALLOWED)
    dim2.append(
        {
            "ok": True,
            "chosen_capability": name,
            "valid_choice": valid_choice,
            "n_tools_offered": len(ALL_TOOLS),
            "outcome": result.outcome,
            "latency_s": round(dt, 1),
        }
    )
    print(f"[2] trial {i + 1}/3: chose={name!r} valid={valid_choice} outcome={result.outcome}")
results["dimensions"]["full_menu_open_ended"] = dim2

# --- 3. no good tool match ------------------------------------------------------
NO_MATCH_INSTRUCTION = (
    f"What is the current stock price of the company behind {ORG_REPO}? "
    "Only use a tool if one of the available tools can actually answer this."
)
dim3 = []
for i in range(3):
    ok, msg, dt = plan("qwen3-next", NO_MATCH_INSTRUCTION, ALL_TOOLS)
    if not ok:
        dim3.append({"ok": False, "error": msg.get("error")})
        print(f"[3] trial {i + 1}/3: request FAILED {msg.get('error')}")
        continue
    tool_calls = msg.get("tool_calls") or []
    if not tool_calls:
        dim3.append({"ok": True, "outcome": "correctly_no_tool_call"})
        print(f"[3] trial {i + 1}/3: correctly called no tool")
        continue
    name = tool_calls[0]["function"]["name"]
    result = dispatcher.dispatch_tool_call(tool_calls[0], allowed_permissions=ALLOWED)
    dim3.append(
        {
            "ok": True,
            "outcome": "over_eager_tool_call",
            "chosen_capability": name,
            "dispatch_outcome": result.outcome,
        }
    )
    print(f"[3] trial {i + 1}/3: OVER-EAGER tool call -- chose={name!r} dispatch={result.outcome}")
results["dimensions"]["no_good_match"] = dim3

# --- 4. gpt-oss single-tool dispatch (the shipped engine's actual default) ----
gpt_oss_tool = registry.get("inspect_repository").to_tool_schema()
dim4 = []
for i in range(3):
    ok, msg, dt = plan("gpt-oss", CAPABILITY_INSTRUCTIONS["inspect_repository"], [gpt_oss_tool])
    if not ok:
        dim4.append({"ok": False, "error": msg.get("error")})
        print(f"[4] gpt-oss trial {i + 1}/3: request FAILED {msg.get('error')}")
        continue
    tool_calls = msg.get("tool_calls") or []
    if not tool_calls:
        dim4.append({"ok": True, "outcome": "no_tool_call", "content": msg.get("content")})
        print(f"[4] gpt-oss trial {i + 1}/3: NO TOOL CALL")
        continue
    result = dispatcher.dispatch_tool_call(tool_calls[0], allowed_permissions=ALLOWED)
    dim4.append(
        {"ok": True, "outcome": result.outcome, "error": result.error, "latency_s": round(dt, 1)}
    )
    print(f"[4] gpt-oss trial {i + 1}/3: dispatch outcome={result.outcome} {dt:.1f}s")
results["dimensions"]["gpt_oss_single_tool"] = dim4

# --- write redacted evidence -------------------------------------------------
raw = json.dumps(results, indent=2, default=str)
(OUT_DIR / "robustness-results.json").write_text(redact(raw), encoding="utf-8")
print(f"\nwrote: {(OUT_DIR / 'robustness-results.json').relative_to(REPO_ROOT)}")
