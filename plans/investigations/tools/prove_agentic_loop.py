# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Wave 1 spike (sprint Task 14): prove one observe -> plan -> execute -> observe -> replan
loop iteration end to end, live, against the real llm.professionalize.com gateway and one real
allow-listed pilot repository -- read-only throughout, no git writes, no pushes.

This is deliberately NOT the Wave 2 CapabilityManifest/registry or the Wave 5 production
supervisor. The "capability menu" below is a tiny, throwaway dict scoped to this spike only,
wrapping three already-existing, already-proven, read-only functions. Its only job is to prove
the loop mechanics (decision `AGT-002`'s acceptance bar) work against this specific weak gateway,
using native tool-calling per `llm-gateway-characterization.md` findings L6/L7 (structured-action
dispatch as a tool call, one capability offered/selected per planning turn, not freeform JSON).

Model: qwen3-next (the routing-recommended model for instruction-critical/planning steps, per
L2/L3/L6 and `runtime-framework-evaluation.md`). gpt-oss's tool-calling was already separately
verified reliable in probe_llm_gateway.py probes 5-6 (parallel excluded, per L7) -- not re-run
here to keep this spike's evidence focused on one clean trace.
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
from readme_agent.evidence.redaction import redact  # noqa: E402
from readme_agent.gitsafety.clone import clone_baseline  # noqa: E402
from readme_agent.inspection import file_inventory  # noqa: E402
from readme_agent.license.auditor import detect_license  # noqa: E402
from readme_agent.orchestrator import inspect_repo  # noqa: E402
from readme_agent.paths import baseline_dir  # noqa: E402
from readme_agent.readme.gap_detector import detect as detect_gaps  # noqa: E402
from readme_agent.registry.loader import find_entry  # noqa: E402

BASE = env.llm_base_url().rstrip("/")
KEY = env.llm_api_key()
HDRS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
TIMEOUT = 90
MODEL = "qwen3-next"
ORG_REPO = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Java"  # allow-listed, mode: dry_run pilot

OUT_DIR = REPO_ROOT / "plans" / "investigations" / "evidence" / "agentic-loop-proof"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# --- capability implementations (wrap existing, proven, read-only functions) ------------------
def _clone_and_scan(org_repo: str):
    entry = find_entry(org_repo)
    if entry is None or entry.mode == "disabled":
        raise PermissionError(f"{org_repo} is not allow-listed with an enabled mode")
    path = baseline_dir(entry.org, entry.repo_name)
    clone_baseline(entry, path)
    inventory = file_inventory.scan(path)
    readme_text = inventory.readme_path.read_text(encoding="utf-8") if inventory.readme_path else ""
    return entry, inventory, readme_text


def cap_inspect_repository(org_repo: str) -> dict:
    r = inspect_repo(org_repo, check_install=False)
    return {
        "org_repo": r["org_repo"],
        "has_readme": r["has_readme"],
        "has_license_file": r["has_license_file"],
        "readme_length_chars": r["readme_length_chars"],
        "manifest_keys": sorted(r["manifest"].keys()) if r["manifest"] else [],
    }


def cap_detect_readme_gaps(org_repo: str) -> dict:
    _entry, inventory, readme_text = _clone_and_scan(org_repo)
    license_state = detect_license(None, inventory.license_path)
    gap_report = detect_gaps(readme_text, license_state.detected)
    flags = {
        "license_mentioned": gap_report.license_mentioned,
        "products_org_link": gap_report.products_org_link,
        "products_com_link": gap_report.products_com_link,
        "relationship_explained": gap_report.relationship_explained,
    }
    return {**flags, "total_gaps": sum(1 for v in flags.values() if not v)}


def cap_check_install_path(org_repo: str) -> dict:
    r = inspect_repo(org_repo, check_install=True)
    pres = r["presentation_report"]
    return {
        "install_path_resolved": pres.install_path_resolved,
        "evidence": pres.evidence.get("install_path_resolved"),
    }


CAPABILITIES = {
    "inspect_repository": {
        "fn": cap_inspect_repository,
        "tool": {
            "type": "function",
            "function": {
                "name": "inspect_repository",
                "description": "Read-only: fetch basic repo facts (README presence/length, "
                "license file presence, manifest keys). No network writes.",
                "parameters": {
                    "type": "object",
                    "properties": {"org_repo": {"type": "string"}},
                    "required": ["org_repo"],
                },
            },
        },
    },
    "detect_readme_gaps": {
        "fn": cap_detect_readme_gaps,
        "tool": {
            "type": "function",
            "function": {
                "name": "detect_readme_gaps",
                "description": "Read-only: scan the README for the four required presentation "
                "elements (license mention, org link, com link, relationship explanation) and "
                "count how many are missing.",
                "parameters": {
                    "type": "object",
                    "properties": {"org_repo": {"type": "string"}},
                    "required": ["org_repo"],
                },
            },
        },
    },
    "check_install_path": {
        "fn": cap_check_install_path,
        "tool": {
            "type": "function",
            "function": {
                "name": "check_install_path",
                "description": "Read-only, live: resolve the repository's install path against "
                "the real package registry (e.g. Maven Central) if the ecosystem supports it.",
                "parameters": {
                    "type": "object",
                    "properties": {"org_repo": {"type": "string"}},
                    "required": ["org_repo"],
                },
            },
        },
    },
    "stop_and_report": {
        "fn": None,
        "tool": {
            "type": "function",
            "function": {
                "name": "stop_and_report",
                "description": "Call this once you have enough information and no further "
                "capability is needed. Ends the loop.",
                "parameters": {
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                    "required": ["summary"],
                },
            },
        },
    },
}
ALL_TOOLS = [c["tool"] for c in CAPABILITIES.values()]

SYSTEM_PROMPT = (
    "You are a read-only repository-inspection planner. You have a menu of capabilities "
    "(tools). Given the current observation, call exactly one capability per turn that would "
    "most usefully extend your understanding of the repository's presentation quality. Once "
    "you have inspected the repository, checked its README gaps, and (if relevant) its install "
    "path, call stop_and_report with a one-sentence summary. Never call a capability you have "
    "already called."
)


def chat_raw(messages: list[dict], tools: list[dict]) -> tuple[bool, dict, float]:
    t0 = time.time()
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 300,
    }
    try:
        r = requests.post(f"{BASE}/chat/completions", headers=HDRS, json=payload, timeout=TIMEOUT)
        dt = time.time() - t0
        if r.status_code != 200:
            return False, {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, dt
        return True, r.json()["choices"][0]["message"], dt
    except Exception as e:  # noqa: BLE001
        return False, {"error": f"{type(e).__name__}: {e}"}, time.time() - t0


def run_loop(org_repo: str, max_rounds: int = 4) -> dict:
    """observe -> plan -> execute -> observe -> replan, capped at max_rounds as a spike-only
    safety net (not a production convergence design -- that's Wave 5)."""
    trace: list[dict] = []
    called: set[str] = set()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Repository: {org_repo}. No observations yet. Plan the first step.",
        },
    ]

    for round_num in range(1, max_rounds + 1):
        ok, msg, dt = chat_raw(messages, ALL_TOOLS)
        round_record: dict = {
            "round": round_num,
            "plan_ok": ok,
            "plan_latency_s": round(dt, 1),
        }
        if not ok:
            round_record["error"] = msg.get("error")
            trace.append(round_record)
            break

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            round_record["outcome"] = "no_tool_call_returned"
            round_record["content"] = msg.get("content")
            trace.append(round_record)
            break

        call = tool_calls[0]  # one capability per turn, per L7
        name = call["function"]["name"]
        try:
            args = json.loads(call["function"]["arguments"])
        except json.JSONDecodeError as e:
            round_record["outcome"] = "invalid_arguments_json"
            round_record["error"] = str(e)
            trace.append(round_record)
            break

        round_record["capability_requested"] = name
        round_record["arguments"] = args

        if name == "stop_and_report":
            round_record["outcome"] = "converged"
            round_record["summary"] = args.get("summary")
            trace.append(round_record)
            break

        if name not in CAPABILITIES:
            round_record["outcome"] = "rejected_unknown_capability"
            trace.append(round_record)
            break  # dispatcher gate: never execute an unregistered capability_id

        if name in called:
            round_record["outcome"] = "rejected_duplicate_capability"
            trace.append(round_record)
            break

        try:
            result = CAPABILITIES[name]["fn"](args.get("org_repo", org_repo))
            round_record["outcome"] = "executed"
            round_record["result"] = result
        except Exception as e:  # noqa: BLE001
            round_record["outcome"] = "execution_error"
            round_record["error"] = f"{type(e).__name__}: {e}"
            trace.append(round_record)
            break

        called.add(name)
        trace.append(round_record)

        # feed the real result back for the replan turn
        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": [call]})
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id", ""),
                "content": json.dumps(result),
            }
        )

    return {
        "org_repo": org_repo,
        "model": MODEL,
        "max_rounds": max_rounds,
        "rounds_used": len(trace),
        "capabilities_called": sorted(called),
        "converged": trace[-1].get("outcome") == "converged" if trace else False,
        "trace": trace,
    }


if __name__ == "__main__":
    result = run_loop(ORG_REPO)
    for r in result["trace"]:
        print(
            f"[round {r['round']}] plan_ok={r['plan_ok']} "
            f"capability={r.get('capability_requested')} outcome={r.get('outcome')}"
        )
    print(f"\nconverged={result['converged']} capabilities_called={result['capabilities_called']}")

    raw = json.dumps(result, indent=2, default=str)
    out_path = OUT_DIR / "loop-trace.json"
    out_path.write_text(redact(raw), encoding="utf-8")
    print(f"\nwrote: {out_path.relative_to(REPO_ROOT)}")
