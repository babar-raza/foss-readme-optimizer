"""Close the three highest-priority qwen3-next capability-probe gaps (2026-08-18).

The 2026-08-18 probe-coverage audit found production relies on behaviors no
probe ever exercised:

1. Forced-NAMED-tool transport shape -- every structured production call uses
   `tool_choice={"type": "function", "function": {"name": ...}}`
   (`llm/verifier_client.py`), but the only tool-calling probes used
   `tool_choice="auto"`.
2. Maximum reliable structured-output size -- every `max_tokens` in the
   codebase (300..12000) was set reactively after a truncation incident; no
   ladder was ever measured.
3. Byte determinism at temperature zero -- cache keys assume reproducibility;
   no probe ever diffed two identical requests.

Read-only against the gateway; writes one evidence JSON. Never logs the key.

Usage:
    .venv/Scripts/python plans/investigations/tools/probe_qwen_output_limits.py \
        [--model qwen3-next] [--trials 5]

Output: plans/investigations/evidence/llm-probe/qwen-output-limits-<date>.json
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = os.environ.get("LLM_BASE_URL", "https://llm.professionalize.com/v1")
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence" / "llm-probe"

NESTED_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "record_findings",
        "description": "Record structured review findings.",
        "parameters": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["approve", "reject"]},
                "findings": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                            "evidence_quote": {"type": "string"},
                        },
                        "required": ["title", "severity", "evidence_quote"],
                        "additionalProperties": False,
                    },
                },
                "summary": {"type": "string"},
            },
            "required": ["verdict", "findings", "summary"],
            "additionalProperties": False,
        },
    },
}


def _call(payload: dict, api_key: str) -> tuple[dict, float]:
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=300) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body, round(time.monotonic() - started, 2)


def probe_forced_named_tool(model: str, trials: int, api_key: str) -> dict:
    """Exactly one correctly-named tool call with schema-valid arguments, N trials."""

    results = []
    for index in range(trials):
        payload = {
            "model": model,
            "temperature": 0.0,
            "max_tokens": 1600,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Review this claim for probe trial "
                        f"{index}: 'The library reads XLSX files.' Provide exactly two "
                        "findings with verbatim evidence quotes from the claim."
                    ),
                }
            ],
            "tools": [NESTED_TOOL_SCHEMA],
            "tool_choice": {"type": "function", "function": {"name": "record_findings"}},
        }
        try:
            body, latency = _call(payload, api_key)
            message = body["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            ok_shape = len(calls) == 1 and calls[0]["function"]["name"] == "record_findings"
            arguments_valid = False
            argument_keys: list[str] = []
            if ok_shape:
                try:
                    arguments = json.loads(calls[0]["function"]["arguments"])
                    argument_keys = sorted(arguments)
                    arguments_valid = (
                        arguments.get("verdict") in {"approve", "reject"}
                        and isinstance(arguments.get("findings"), list)
                        and all(
                            {"title", "severity", "evidence_quote"} <= set(item)
                            for item in arguments["findings"]
                        )
                        and isinstance(arguments.get("summary"), str)
                    )
                except (json.JSONDecodeError, TypeError):
                    arguments_valid = False
            results.append(
                {
                    "trial": index,
                    "exactly_one_named_call": ok_shape,
                    "arguments_schema_valid": arguments_valid,
                    "argument_keys": argument_keys,
                    "finish_reason": body["choices"][0].get("finish_reason"),
                    "completion_tokens": body.get("usage", {}).get("completion_tokens"),
                    "latency_s": latency,
                }
            )
        except Exception as exc:  # noqa: BLE001 -- probe records failures as data
            results.append({"trial": index, "error": f"{type(exc).__name__}: {exc}"})
    return {"results": results}


def probe_output_size_ladder(model: str, api_key: str) -> dict:
    """Ask for exact-count JSON arrays; find where completion degrades."""

    ladder = []
    for item_count in (25, 50, 100, 200, 400):
        payload = {
            "model": model,
            "temperature": 0.0,
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Return ONLY a JSON array (no code fence) with exactly "
                        f"{item_count} objects. Object i must be "
                        '{"id": i, "name": "item-i", "description": "a deterministic '
                        "twelve word description sentence for structured output probing "
                        'purposes only."}. Number ids 0..'
                        f"{item_count - 1}."
                    ),
                }
            ],
        }
        try:
            body, latency = _call(payload, api_key)
            content = body["choices"][0]["message"].get("content") or ""
            finish = body["choices"][0].get("finish_reason")
            parsed_count = None
            parse_ok = False
            try:
                data = json.loads(content)
                parse_ok = isinstance(data, list)
                parsed_count = len(data) if parse_ok else None
            except json.JSONDecodeError:
                parse_ok = False
            ladder.append(
                {
                    "requested_items": item_count,
                    "parse_ok": parse_ok,
                    "parsed_items": parsed_count,
                    "exact_count": parsed_count == item_count,
                    "finish_reason": finish,
                    "completion_tokens": body.get("usage", {}).get("completion_tokens"),
                    "content_chars": len(content),
                    "latency_s": latency,
                }
            )
        except Exception as exc:  # noqa: BLE001
            ladder.append({"requested_items": item_count, "error": f"{type(exc).__name__}: {exc}"})
    return {"ladder": ladder}


def probe_temperature_zero_determinism(model: str, trials: int, api_key: str) -> dict:
    """Byte-compare repeated identical requests, freeform and forced-tool."""

    freeform_payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 700,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Write a six-sentence factual paragraph explaining what a JSON schema "
                    "is. No preamble."
                ),
            }
        ],
    }
    tool_payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 1200,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Review this claim: 'The parser accepts UTF-8 input.' Provide exactly "
                    "two findings with verbatim evidence quotes from the claim."
                ),
            }
        ],
        "tools": [NESTED_TOOL_SCHEMA],
        "tool_choice": {"type": "function", "function": {"name": "record_findings"}},
    }
    outcome: dict[str, dict] = {}
    for label, payload in (("freeform", freeform_payload), ("forced_tool", tool_payload)):
        observed: list[str] = []
        errors: list[str] = []
        for _ in range(trials):
            try:
                body, _latency = _call(payload, api_key)
                message = body["choices"][0]["message"]
                if label == "freeform":
                    observed.append(message.get("content") or "")
                else:
                    calls = message.get("tool_calls") or []
                    observed.append(calls[0]["function"]["arguments"] if calls else "")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}")
        distinct = sorted({item for item in observed})
        outcome[label] = {
            "trials": trials,
            "errors": errors,
            "distinct_outputs": len(distinct),
            "byte_deterministic": len(distinct) == 1 and not errors,
            "output_lengths": [len(item) for item in observed],
        }
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3-next")
    parser.add_argument("--trials", type=int, default=5)
    args = parser.parse_args()
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        print("error: LLM_API_KEY is not set")
        return 2
    evidence = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_url_host": BASE_URL.split("//", 1)[-1].split("/", 1)[0],
        "model": args.model,
        "probes": {
            "forced_named_tool": probe_forced_named_tool(args.model, args.trials, api_key),
            "output_size_ladder": probe_output_size_ladder(args.model, api_key),
            "temperature_zero_determinism": probe_temperature_zero_determinism(
                args.model, args.trials, api_key
            ),
        },
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EVIDENCE_DIR / (f"qwen-output-limits-{datetime.now(UTC).strftime('%Y%m%d')}.json")
    out_path.write_text(json.dumps(evidence, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"evidence written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
