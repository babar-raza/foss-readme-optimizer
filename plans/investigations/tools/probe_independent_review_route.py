# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Live characterization of the llm.professionalize.com gateway for the NEW independent
README-quality-reviewer job (RPOC-020, plans/investigations/executive-verdict-the-swirling-adleman
Part B.2 Lane V). Reuses `probe_llm_gateway.py`'s methodology (live calls, N-trial reliability,
the gateway's own `usage.prompt_tokens` as ground truth for context size -- never a client-side
estimate, per `llm-gateway-context-ceiling-corrected.md`'s own corrected discipline) but targets
this job's actual shape, which none of the existing routed jobs share:

  - long-context (grounding facts + repository excerpts + a full README candidate, tens of
    thousands of tokens)
  - strict structured JSON matching a 5-way verdict taxonomy (`ACCEPT` / `REJECT_REPAIRABLE` /
    `BLOCKED_FACT_CONFLICT` / `BLOCKED_MISSING_EVIDENCE` / `SYSTEM_FAILURE`) with nested
    per-criterion reasoning fields
  - genuine quality judgment, not just tool-calling or schema reliability: can the model actually
    tell a well-grounded, specific README apart from a generic templated one, a README that
    contradicts the given facts, and a README that makes claims no given fact supports?

Probes:
  1. GET  /models                    -> confirm inventory remains unchanged since the gateway
                                         characterization investigation
  2. POST /chat/completions          -> alias identity check (is "recommended"/"experimental" a
                                         distinct model from qwen3-next/gpt-oss, or an alias?)
  3. POST /chat/completions          -> 4-way discrimination test (well-grounded-specific /
                                         generic-template-overpromotion / fact-conflict /
                                         missing-evidence), scored against the verdict a careful
                                         human reviewer would give, for each chat model
  4. POST /chat/completions          -> long-context version of the well-grounded-specific
                                         scenario, padded with realistic (not lorem-ipsum)
                                         supporting repository evidence to tens of thousands of
                                         real tokens, with an embedded mid-context needle to prove
                                         the model actually reads deep context while still
                                         returning a valid, correct verdict
  5. POST /chat/completions          -> N=3 repeat of probe 4 for the leading candidate, to check
                                         verdict/JSON stability at long context (not just N=1)

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
TIMEOUT = 120

OUT_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "independent-readme-reviewer-route-characterization-2026-07-25"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

results: dict = {"base_url_host": BASE.split("//")[-1].split("/")[0], "probes": {}}


def chat(model: str, content: str, max_tokens: int = 900) -> tuple[bool, str, float, dict]:
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
            return False, f"HTTP {r.status_code}: {r.text[:300]}", dt, {}
        d = r.json()
        return True, d["choices"][0]["message"]["content"] or "", dt, d.get("usage", {})
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}", time.time() - t0, {}


# --- 1. model inventory (confirm unchanged) ----------------------------------
try:
    r = requests.get(f"{BASE}/models", headers=HDRS, timeout=TIMEOUT)
    models = [m["id"] for m in r.json().get("data", [])] if r.status_code == 200 else []
    results["probes"]["models"] = {"status": r.status_code, "ids": models}
except Exception as e:  # noqa: BLE001
    results["probes"]["models"] = {"error": str(e)}
    models = []
print(f"[1] models: {results['probes']['models']}")

chat_models = [m for m in models if m in ("qwen3-next", "gpt-oss")]
# Qwen2.5-VL-7B is a distinct third real chat-capable model on this gateway (confirmed not an
# alias of either named chat model -- it is the only vision-capable model, per
# llm-gateway-characterization.md L5). It fails tool-calling entirely (L6) but this new job needs
# no tool-calling, only freeform structured JSON at long context, where the ORIGINAL
# characterization found it 5/5 (L3) -- worth a real discrimination test here rather than
# excluding it on an L6 finding that doesn't actually apply to this job's shape.
vision_model = [m for m in models if m == "Qwen2.5-VL-7B"]
discrimination_models = chat_models + vision_model
alias_models = [m for m in models if m in ("recommended", "experimental")]

# --- 2. alias identity check --------------------------------------------------
# "recommended"/"experimental" appear in /models alongside the two named chat models. Send the
# identical deterministic (temperature=0) prompt to all four and diff the raw text: if an alias's
# output is byte-identical to a named model's, it is that model under another name, not a
# distinct third/fourth candidate -- decides whether this job's characterization needs >2 models.
IDENTITY_PROMPT = "Reply with exactly one line: the word OK followed by the digits 7 4 1 9."
alias_check: dict = {}
identity_outputs: dict = {}
for model in chat_models + alias_models:
    ok, out, dt, _usage = chat(model, IDENTITY_PROMPT, max_tokens=20)
    identity_outputs[model] = out.strip()
    alias_check[model] = {"ok": ok, "output": out.strip(), "latency_s": round(dt, 1)}
    print(f"[2] {model}: ok={ok} output={out.strip()!r} {dt:.1f}s")
for alias in alias_models:
    matches = [m for m in chat_models if identity_outputs.get(m) == identity_outputs.get(alias)]
    alias_check[alias]["matches_named_model"] = matches or None
results["probes"]["alias_identity_check"] = alias_check

# --- shared grounding facts for the discrimination + long-context probes -----
# A fictional Java library (continuing this project's own established fictional-product
# convention from probe_llm_gateway.py's SCHEMA_PROMPT, "AcmeCells") with a rich, specific,
# internally-consistent fact set a real independent-reviewer job would be given: capabilities,
# unsupported formats, explicit limitations, verified acquisition, license, and a verified
# minimal example. Every discrimination scenario below is graded against THIS fact set.
GROUNDING_FACTS = {
    "product_name": "AcmeCells",
    "language": "Java",
    "audience": "Java backend developers who need to generate or edit Excel-compatible "
    "spreadsheets without depending on Microsoft Office being installed on the server",
    "capabilities": [
        "Read and write .xlsx workbooks",
        "Apply cell styles, number formats, and conditional formatting",
        "Evaluate a subset of built-in Excel formulas (SUM, AVERAGE, VLOOKUP, IF -- 40 total, "
        "listed in docs/formulas.md)",
    ],
    "formats_supported": ["xlsx"],
    "formats_explicitly_not_supported": ["xls (legacy binary format)", "ods"],
    "limitations": [
        "No support for VBA macros",
        "No support for pivot tables",
        "Formula evaluation is limited to the 40 functions listed in docs/formulas.md -- "
        "unlisted functions are preserved as text but not recalculated",
    ],
    "installation": {
        "method": "Maven Central",
        "verified_acquisition": True,
        "coordinates": "com.acmesoft:acme-cells:3.2.0",
        "verification_note": "GAV resolved live against Maven Central on 2026-07-24; artifact "
        "present, checksums match",
    },
    "license": "Apache-2.0",
    "minimal_example_verified": True,
    "minimal_example_summary": "A 12-line Java example that creates a workbook, writes 3 cells, "
    "applies a currency number format, and saves to disk -- compiled and executed live against "
    "the real Maven artifact",
}

VERDICT_SCHEMA_INSTRUCTIONS = (
    "You are an independent README-quality reviewer. You are given (1) verified grounding facts "
    "about a software product, and (2) a candidate README for that product. Your job is to "
    "judge the candidate strictly against the grounding facts -- never against general writing "
    "taste alone -- and return EXACTLY one of these five verdicts:\n"
    "  ACCEPT -- the candidate is specific, accurate, and fully supported by the grounding facts.\n"
    "  REJECT_REPAIRABLE -- the candidate is generic/templated/overpromotional or otherwise weak, "
    "but nothing in it actually contradicts or lacks support from the grounding facts; a rewrite "
    "could fix it.\n"
    "  BLOCKED_FACT_CONFLICT -- the candidate makes at least one claim that directly contradicts "
    "a given grounding fact.\n"
    "  BLOCKED_MISSING_EVIDENCE -- the candidate makes at least one specific, checkable claim "
    "(a number, a benchmark, a capability, a scale claim, etc.) that no grounding fact supports "
    "or refutes -- it is simply unverifiable from what you were given.\n"
    "  SYSTEM_FAILURE -- you cannot perform the review at all (e.g. the input is truncated, "
    "unreadable, or self-contradictory in a way that makes review impossible).\n\n"
    "Return ONLY a JSON object (no prose, no markdown code fences) with exactly this shape:\n"
    "{\n"
    '  "verdict": one of the five words above,\n'
    '  "confidence": number 0..1,\n'
    '  "reasoning": {\n'
    '    "product_specificity": short string,\n'
    '    "overpromotion_check": short string,\n'
    '    "readability": short string,\n'
    '    "generic_template_symptoms": short string,\n'
    '    "fact_conflicts": array of {"claim": string, "conflicting_fact": string} '
    "(empty array if none),\n"
    '    "missing_evidence": array of {"claim": string, "reason": string} '
    "(empty array if none)\n"
    "  },\n"
    '  "summary": short string\n'
    "}\n"
)

CANDIDATES = {
    "well_grounded_specific": {
        "expected_verdict": "ACCEPT",
        "readme": (
            "# AcmeCells\n\n"
            "AcmeCells is a Java library for reading and writing `.xlsx` workbooks on the JVM, "
            "for backend developers who need spreadsheet generation without Microsoft Office "
            "installed on the server.\n\n"
            "## Capabilities\n"
            "- Read and write `.xlsx` workbooks\n"
            "- Apply cell styles, number formats, and conditional formatting\n"
            "- Evaluate 40 built-in Excel formulas (SUM, AVERAGE, VLOOKUP, IF, and 36 others -- "
            "full list in `docs/formulas.md`); functions outside this list are preserved as text, "
            "not recalculated\n\n"
            "## Not supported\n"
            "- Legacy `.xls` binary format, or `.ods`\n"
            "- VBA macros\n"
            "- Pivot tables\n\n"
            "## Install (Maven Central)\n"
            "```xml\n<dependency>\n  <groupId>com.acmesoft</groupId>\n"
            "  <artifactId>acme-cells</artifactId>\n  <version>3.2.0</version>\n</dependency>\n"
            "```\n\n"
            "## Minimal example\n"
            "A 12-line example that creates a workbook, writes 3 cells, applies a currency "
            "number format, and saves to disk is in `examples/Minimal.java`.\n\n"
            "## License\nApache-2.0\n"
        ),
    },
    "generic_template_overpromotion": {
        "expected_verdict": "REJECT_REPAIRABLE",
        "readme": (
            "# AcmeCells\n\n"
            "AcmeCells is a next-generation, enterprise-grade, blazing-fast spreadsheet solution "
            "trusted by developers worldwide. Effortlessly handle any spreadsheet workflow with "
            "zero configuration and maximum flexibility.\n\n"
            "## Why AcmeCells?\n"
            "- Lightning-fast performance\n"
            "- Rock-solid reliability\n"
            "- Seamless integration with your existing stack\n"
            "- Loved by developers everywhere\n\n"
            "## Getting started\n"
            "Install the package for your platform and follow the quick-start guide to get up "
            "and running in seconds.\n\n"
            "## Support\n"
            "Join our community for help and best practices.\n"
        ),
    },
    "fact_conflict": {
        "expected_verdict": "BLOCKED_FACT_CONFLICT",
        "readme": (
            "# AcmeCells\n\n"
            "AcmeCells is a full-featured spreadsheet library with complete support for legacy "
            "`.xls` files, modern `.xlsx` workbooks, and full VBA macro execution. Pivot table "
            "generation is fully supported out of the box.\n\n"
            "## Install\n"
            "```bash\npip install acmecells\n```\n\n"
            "## Capabilities\n"
            "- Read/write `.xls`, `.xlsx`\n"
            "- Run existing VBA macros unmodified\n"
            "- Generate and refresh pivot tables\n"
            "- Evaluate every Excel formula, no exceptions\n\n"
            "## License\nApache-2.0\n"
        ),
    },
    "missing_evidence": {
        "expected_verdict": "BLOCKED_MISSING_EVIDENCE",
        "readme": (
            "# AcmeCells\n\n"
            "AcmeCells is a Java library for `.xlsx` workbook generation, benchmarked at over "
            "50,000 rows/second on commodity hardware and used in production by more than 200 "
            "enterprise customers. Streaming writes are supported for files larger than 2GB "
            "without exceeding a fixed memory ceiling.\n\n"
            "## Capabilities\n"
            "- Read and write `.xlsx` workbooks\n"
            "- Apply cell styles and number formats\n"
            "- Evaluate common Excel formulas\n\n"
            "## Install (Maven Central)\n"
            "```xml\n<dependency>\n  <groupId>com.acmesoft</groupId>\n"
            "  <artifactId>acme-cells</artifactId>\n  <version>3.2.0</version>\n</dependency>\n"
            "```\n\n"
            "## License\nApache-2.0\n"
        ),
    },
}


def build_review_prompt(readme_text: str, extra_context: str = "") -> str:
    return (
        VERDICT_SCHEMA_INSTRUCTIONS
        + "\n\n=== GROUNDING FACTS (JSON) ===\n"
        + json.dumps(GROUNDING_FACTS, indent=2)
        + (("\n\n=== SUPPORTING REPOSITORY CONTEXT ===\n" + extra_context) if extra_context else "")
        + "\n\n=== CANDIDATE README ===\n"
        + readme_text
        + "\n\n=== END CANDIDATE README ===\nReturn the JSON verdict object now."
    )


VALID_VERDICTS = {
    "ACCEPT",
    "REJECT_REPAIRABLE",
    "BLOCKED_FACT_CONFLICT",
    "BLOCKED_MISSING_EVIDENCE",
    "SYSTEM_FAILURE",
}


def parse_verdict(txt: str) -> tuple[bool, dict | None, str]:
    t = txt.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0] if "```" in t else t
    try:
        d = json.loads(t)
    except Exception as e:  # noqa: BLE001
        return False, None, f"json:{e}"
    if not isinstance(d, dict):
        return False, None, "not-a-dict"
    if d.get("verdict") not in VALID_VERDICTS:
        return False, d, f"bad-verdict:{d.get('verdict')!r}"
    reasoning = d.get("reasoning")
    if not isinstance(reasoning, dict):
        return False, d, "reasoning-not-dict"
    required_reasoning_keys = {
        "product_specificity",
        "overpromotion_check",
        "readability",
        "generic_template_symptoms",
        "fact_conflicts",
        "missing_evidence",
    }
    if not required_reasoning_keys.issubset(reasoning.keys()):
        return False, d, f"missing-reasoning-keys:{required_reasoning_keys - reasoning.keys()}"
    if not isinstance(reasoning.get("fact_conflicts"), list) or not isinstance(
        reasoning.get("missing_evidence"), list
    ):
        return False, d, "conflict/missing lists wrong type"
    if not isinstance(d.get("confidence"), (int, float)):
        return False, d, "confidence-not-number"
    return True, d, "schema-ok"


# --- 3. discrimination test ---------------------------------------------------
# max_tokens=1600 (raised from an initial 900 mid-investigation): the first live pass at 900
# truncated 2/4 gpt-oss responses mid-JSON (verbose fact_conflicts/missing_evidence arrays ran
# out of budget before the closing brace) while every qwen3-next response fit comfortably --
# a real token-cost difference between the two models, but a budget confound for a fair
# apples-to-apples discrimination comparison, so it is corrected here rather than reported as a
# qwen3-next-favoring artifact of an arbitrary limit.
DISCRIMINATION_MAX_TOKENS = 1600
discrimination: dict = {}
for model in discrimination_models:
    model_results = {}
    for scenario_name, scenario in CANDIDATES.items():
        prompt = build_review_prompt(scenario["readme"])
        ok, out, dt, usage = chat(model, prompt, max_tokens=DISCRIMINATION_MAX_TOKENS)
        valid, parsed, why = parse_verdict(out) if ok else (False, None, out[:200])
        verdict = parsed.get("verdict") if parsed else None
        correct = valid and verdict == scenario["expected_verdict"]
        model_results[scenario_name] = {
            "ok": ok,
            "schema_valid": valid,
            "why": why,
            "expected_verdict": scenario["expected_verdict"],
            "actual_verdict": verdict,
            "correct": correct,
            "prompt_tokens": usage.get("prompt_tokens"),
            "latency_s": round(dt, 1),
            "raw_response": out,
        }
        print(
            f"[3] {model} / {scenario_name}: ok={ok} valid={valid} "
            f"expected={scenario['expected_verdict']} actual={verdict} correct={correct} "
            f"{dt:.1f}s"
        )
    n_scenarios = len(CANDIDATES)
    model_results["_summary"] = {
        "schema_valid_rate": sum(
            1 for k, v in model_results.items() if not k.startswith("_") and v["schema_valid"]
        )
        / n_scenarios,
        "correct_verdict_rate": sum(
            1 for k, v in model_results.items() if not k.startswith("_") and v["correct"]
        )
        / n_scenarios,
    }
    discrimination[model] = model_results
results["probes"]["discrimination"] = discrimination

# --- 4. long-context version of well_grounded_specific, w/ mid-context needle -
# Realistic (not lorem-ipsum) padding: a verbose synthetic formulas doc + changelog, thematically
# consistent with GROUNDING_FACTS/the AcmeCells product, standing in for the repository excerpts
# a real independent-review job would be given alongside the facts. A unique needle sentence is
# embedded partway through so a targeted question proves genuine mid-context reading, not just
# start/end attention -- same "prove full-prompt visibility" discipline as
# llm-gateway-context-ceiling-corrected.md's L1' ladder, applied to THIS job's realistic payload
# shape instead of a flat filler string.
_FORMULA_NAMES = [
    "SUM",
    "AVERAGE",
    "VLOOKUP",
    "IF",
    "COUNT",
    "COUNTA",
    "COUNTIF",
    "MAX",
    "MIN",
    "ROUND",
    "CONCATENATE",
    "LEFT",
    "RIGHT",
    "MID",
    "TRIM",
    "UPPER",
    "LOWER",
    "LEN",
    "FIND",
    "SUBSTITUTE",
    "AND",
    "OR",
    "NOT",
    "ISBLANK",
    "ISNUMBER",
    "ISTEXT",
    "TODAY",
    "NOW",
    "DATE",
    "YEAR",
    "MONTH",
    "DAY",
    "ABS",
    "SQRT",
    "POWER",
    "MOD",
    "RANK",
    "MEDIAN",
    "STDEV",
    "VAR",
]
_formula_doc_lines = [
    f"### {name}\n{name} is one of the 40 functions AcmeCells evaluates natively; it behaves "
    f"identically to Excel's own {name} for the argument shapes AcmeCells' parser accepts. "
    f"Any spreadsheet cell using {name} outside those accepted shapes is preserved as literal "
    f"text, per the documented formula-evaluation limitation."
    for name in _FORMULA_NAMES
]
NEEDLE_SENTENCE = (
    "INTERNAL BUILD NOTE (needle-check-only, not a product fact): the codeword for this "
    "context-verification probe is GLYPH-40217."
)


def build_long_context_padding(target_tokens: int) -> tuple[str, str]:
    """Returns (padding_text, needle_sentence). Grows a realistic changelog until the gateway's
    own usage.prompt_tokens (checked by the caller after a real call, not estimated here) is
    expected to land near target_tokens at ~4-5 real chars/token for this kind of prose --
    the caller reports the REAL measured token count, this function only sizes the request."""
    entries = []
    version_major, version_minor, version_patch = 1, 0, 0
    approx_chars_per_entry = 260
    target_chars = target_tokens * 4
    n_entries = max(target_chars // approx_chars_per_entry, 10)
    needle_index = int(n_entries * 0.55)  # embed needle well past the midpoint, before the end
    for i in range(n_entries):
        version_patch += 1
        if version_patch > 9:
            version_patch = 0
            version_minor += 1
        entry = (
            f"### v{version_major}.{version_minor}.{version_patch}\n"
            f"- Internal refactor of the `.xlsx` writer's shared-strings table for entry "
            f"#{i}; no behavior change for callers.\n"
            f"- Expanded test coverage for cell-style inheritance edge case #{i}.\n"
        )
        if i == needle_index:
            entry += f"- {NEEDLE_SENTENCE}\n"
        entries.append(entry)
    changelog = "## docs/formulas.md (excerpt)\n\n" + "\n".join(_formula_doc_lines)
    changelog += "\n\n## CHANGELOG.md (excerpt)\n\n" + "\n".join(entries)
    return changelog, NEEDLE_SENTENCE


LONG_CONTEXT_TARGET_TOKENS = 24_000
padding, needle = build_long_context_padding(LONG_CONTEXT_TARGET_TOKENS)
long_context_prompt_base = build_review_prompt(
    CANDIDATES["well_grounded_specific"]["readme"], extra_context=padding
)
long_context_prompt = long_context_prompt_base.replace(
    '"summary": short string\n}',
    '"summary": short string,\n  "context_check": exact codeword string found in the '
    "supporting repository context above (the string after GLYPH-)\n}",
)

long_context: dict = {}
for model in discrimination_models:
    ok, out, dt, usage = chat(model, long_context_prompt, max_tokens=DISCRIMINATION_MAX_TOKENS)
    valid, parsed, why = parse_verdict(out) if ok else (False, None, out[:200])
    verdict = parsed.get("verdict") if parsed else None
    correct = valid and verdict == "ACCEPT"
    needle_found = ok and "GLYPH-40217" in out
    long_context[model] = {
        "ok": ok,
        "prompt_tokens": usage.get("prompt_tokens"),
        "schema_valid": valid,
        "why": why,
        "actual_verdict": verdict,
        "correct_verdict": correct,
        "needle_found_in_output": needle_found,
        "latency_s": round(dt, 1),
        "raw_response": out,
    }
    print(
        f"[4] {model} long-context: ok={ok} prompt_tokens={usage.get('prompt_tokens')} "
        f"valid={valid} verdict={verdict} correct={correct} needle={needle_found} {dt:.1f}s"
    )
results["probes"]["long_context_well_grounded"] = long_context

# --- 5. N=3 stability repeat of the long-context probe, leading candidate only -
# Bounded (cost/time), mirroring probe_llm_gateway.py's own "Deviation from plan" precedent of
# reduced N for the qwen model where determinism was already observed once (temperature=0).
STABILITY_TRIALS = 3
stability: dict = {}
leading_candidate = (
    "qwen3-next" if "qwen3-next" in chat_models else (chat_models[0] if chat_models else None)
)
if leading_candidate:
    outcomes = []
    for i in range(STABILITY_TRIALS):
        ok, out, dt, usage = chat(
            leading_candidate, long_context_prompt, max_tokens=DISCRIMINATION_MAX_TOKENS
        )
        valid, parsed, why = parse_verdict(out) if ok else (False, None, out[:200])
        verdict = parsed.get("verdict") if parsed else None
        needle_found = ok and "GLYPH-40217" in out
        outcomes.append(
            {
                "trial": i + 1,
                "ok": ok,
                "schema_valid": valid,
                "verdict": verdict,
                "needle_found": needle_found,
                "prompt_tokens": usage.get("prompt_tokens"),
                "latency_s": round(dt, 1),
            }
        )
        print(
            f"[5] {leading_candidate} long-context trial {i + 1}/{STABILITY_TRIALS}: "
            f"valid={valid} verdict={verdict} needle={needle_found} {dt:.1f}s"
        )
    stability[leading_candidate] = {
        "trials": STABILITY_TRIALS,
        "schema_valid_rate": sum(o["schema_valid"] for o in outcomes) / STABILITY_TRIALS,
        "verdict_stable": len({o["verdict"] for o in outcomes}) == 1,
        "needle_recall_rate": sum(o["needle_found"] for o in outcomes) / STABILITY_TRIALS,
        "outcomes": outcomes,
    }
results["probes"]["long_context_stability"] = stability

# --- write redacted evidence -------------------------------------------------
raw = json.dumps(results, indent=2)
(OUT_DIR / "probe-results.json").write_text(redact(raw), encoding="utf-8")
print(f"\nwrote: {(OUT_DIR / 'probe-results.json').relative_to(REPO_ROOT)}")
