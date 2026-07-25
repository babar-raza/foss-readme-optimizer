# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Live characterization of the llm.professionalize.com gateway for the NEW agentic
product_truth-drafting job (RPOC-030, plans/investigations/executive-verdict-the-swirling-adleman
Part B.2 Phase 2 Lane F, design Part C.5). Reuses `probe_independent_review_route.py`'s own
methodology (live calls, N-trial reliability where cheap, the gateway's own `usage.prompt_tokens`
as ground truth for context size, an explicit alias-identity check before assuming >2 real
candidates) but targets THIS job's actual, genuinely different shape:

  - multiple structured output fields per response (audience, problems_solved, capabilities,
    formats, limitations, minimal_example), not one 5-way verdict label
  - every claim in every field must carry a citation (a supporting_fact_id or an evidence_path +
    optional required_symbols) -- faithfulness (never citing something not actually given) matters
    as much as schema validity
  - ecosystem-correct code generation (minimal_example.language must match the given ecosystem),
    which none of the previously-routed jobs need at all

Unlike RPOC-020's own characterization (which reconstructed the verdict schema by hand, since the
real prompt did not exist yet), THIS probe runs against the REAL `prompts/generation/
draft_product_truth.yaml` prompt via the real `llm.prompt_registry`/
`llm.generation_prompts.build_draft_product_truth_messages()` and validates responses with the
REAL `facts.agentic_drafting.DraftProductTruthV1` pydantic model -- both already built by this same
taskcard (RPOC-031-033) before this probe runs, so this is characterization against production code,
not a reconstruction later taskcards would need to re-validate.

Probes:
  1. GET  /models             -> confirm inventory unchanged since llm-gateway-characterization.md
  2. POST /chat/completions   -> alias identity check (only 2 distinct chat models expected,
                                  per llm-gateway-characterization.md and the independent-reviewer
                                  route's own prior confirmation)
  3. POST /chat/completions   -> 2-scenario faithfulness test per model: a well-resourced Java
                                  fictional product (multiple source files, several objective facts)
                                  and a sparse-evidence Python fictional product (one source file,
                                  fewer facts) -- the second scenario specifically tests whether a
                                  model resists the temptation to fabricate a path/fact_id/symbol
                                  when it is given less to work with, and whether it selects the
                                  correct minimal_example.language per ecosystem
  4. POST /chat/completions   -> N=2 repeat of both scenarios for the leading candidate, bounded
                                  (cost/time) per this project's own established reduced-N precedent
                                  for a model already showing zero variance at temperature=0

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
from readme_agent.facts.agentic_drafting import DraftProductTruthV1  # noqa: E402
from readme_agent.llm.generation_prompts import build_draft_product_truth_messages  # noqa: E402

BASE = env.llm_base_url().rstrip("/")
KEY = env.llm_api_key()
HDRS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
TIMEOUT = 120
# Matches `facts/agentic_drafting.py::_MAX_RESPONSE_TOKENS` -- the real budget the production
# client will use for this job, so this probe measures against the actual configured ceiling, not
# an arbitrary one that could hide a real truncation confound (the exact mistake
# `independent-readme-reviewer-route-characterization-2026-07-25` found and corrected for a
# smaller, single-verdict response shape: 900 -> 1600).
MAX_RESPONSE_TOKENS = 3000

OUT_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "draft-product-truth-route-characterization-2026-07-25"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

results: dict = {"base_url_host": BASE.split("//")[-1].split("/")[0], "probes": {}}


def chat(model: str, messages: list[dict], max_tokens: int = MAX_RESPONSE_TOKENS) -> tuple:
    t0 = time.time()
    try:
        r = requests.post(
            f"{BASE}/chat/completions",
            headers=HDRS,
            json={
                "model": model,
                "messages": messages,
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
alias_models = [m for m in models if m in ("recommended", "experimental")]

# --- 2. alias identity check (same technique as the independent-reviewer route's own probe) --
IDENTITY_PROMPT = "Reply with exactly one line: the word OK followed by the digits 5 1 8 3."
alias_check: dict = {}
identity_outputs: dict = {}
for model in chat_models + alias_models:
    ok, out, dt, _usage = chat(model, [{"role": "user", "content": IDENTITY_PROMPT}], max_tokens=20)
    identity_outputs[model] = out.strip()
    alias_check[model] = {"ok": ok, "output": out.strip(), "latency_s": round(dt, 1)}
    print(f"[2] {model}: ok={ok} output={out.strip()!r} {dt:.1f}s")
for alias in alias_models:
    matches = [m for m in chat_models if identity_outputs.get(m) == identity_outputs.get(alias)]
    alias_check[alias]["matches_named_model"] = matches or None
results["probes"]["alias_identity_check"] = alias_check

# --- shared scenario fixtures --------------------------------------------------
# Scenario A: well-resourced fictional Java product, continuing this project's own established
# fictional-product convention ("AcmeCells", probe_llm_gateway.py's SCHEMA_PROMPT and
# probe_independent_review_route.py's GROUNDING_FACTS) -- several objective facts, several source
# files, plenty of real evidence to cite.
_JAVA_FACT_IDS = {
    "product.identity:manifest-and-registry",
    "product.platforms:manifest",
    "installation.coordinates:manifest",
    "installation.verified_acquisition:registry-maven_central",
    "product.license:license-file",
    "release.state:manifest-and-registry",
}
JAVA_FACTS_JSON = json.dumps(
    {
        "org_repo": "acme/acmecells-java",
        "facts": [
            {
                "fact_id": "product.identity:manifest-and-registry",
                "field": "product.identity",
                "value": {
                    "family": "acmecells",
                    "platform": "java",
                    "ecosystem": "java",
                    "repository": "acme/acmecells-java",
                    "manifest_names": ["acme-cells"],
                },
            },
            {
                "fact_id": "product.platforms:manifest",
                "field": "product.platforms",
                "value": ["java"],
            },
            {
                "fact_id": "installation.coordinates:manifest",
                "field": "installation.coordinates",
                "value": [
                    {
                        "path": ".",
                        "ecosystem": "java",
                        "manifest_path": "pom.xml",
                        "group_id": "com.acmesoft",
                        "artifact_id": "acme-cells",
                        "version": "3.2.0",
                    }
                ],
            },
            {
                "fact_id": "installation.verified_acquisition:registry-maven_central",
                "field": "installation.verified_acquisition",
                "value": {
                    "method": "maven_central",
                    "outcome": "REGISTRY_VERIFIED",
                    "coordinate": "com.acmesoft:acme-cells:3.2.0",
                },
            },
            {
                "fact_id": "product.license:license-file",
                "field": "product.license",
                "value": "Apache-2.0",
            },
            {
                "fact_id": "release.state:manifest-and-registry",
                "field": "release.state",
                "value": [{"path": ".", "version": "3.2.0", "active": True}],
            },
        ],
    },
    indent=2,
)
JAVA_CONTEXT_FILES = {
    "README.md": (
        "# AcmeCells\n\nAcmeCells is a Java library for reading and writing `.xlsx` workbooks "
        "on the JVM, for backend developers who need spreadsheet generation without Microsoft "
        "Office installed on the server. Apache-2.0 licensed.\n"
    ),
    "pom.xml": (
        "<project><groupId>com.acmesoft</groupId><artifactId>acme-cells</artifactId>"
        "<version>3.2.0</version></project>\n"
    ),
    "src/main/java/com/acmesoft/cells/Workbook.java": (
        "package com.acmesoft.cells;\n\npublic class Workbook implements AutoCloseable {\n"
        "    public WorksheetCollection getWorksheets() { return null; }\n"
        "    public void save(String fileName) { }\n    public void close() { }\n}\n"
    ),
    "src/main/java/com/acmesoft/cells/Worksheet.java": (
        "package com.acmesoft.cells;\n\npublic class Worksheet {\n"
        "    public CellCollection getCells() { return null; }\n}\n"
    ),
    "src/main/java/com/acmesoft/cells/Cell.java": (
        "package com.acmesoft.cells;\n\npublic class Cell {\n"
        "    public void putValue(String value) { }\n}\n"
    ),
    "src/main/java/com/acmesoft/cells/SaveFormat.java": (
        "package com.acmesoft.cells;\n\npublic final class SaveFormat {\n"
        '    public static final String XLSX = "xlsx";\n}\n'
    ),
}
JAVA_CONTEXT = "".join(f"--- {path} ---\n{text}\n" for path, text in JAVA_CONTEXT_FILES.items())

# Scenario B: sparse-evidence fictional Python product ("AcmeFlux") -- deliberately thin: one
# source file, three objective facts. Tests both ecosystem-correct language selection (python, not
# java) AND whether a model resists inventing extra capabilities/paths when there is genuinely
# little to cite -- the prompt's own instruction is "draft fewer claims, never invent."
_PYTHON_FACT_IDS = {
    "product.identity:manifest-and-registry",
    "product.platforms:manifest",
    "product.license:license-file",
}
PYTHON_FACTS_JSON = json.dumps(
    {
        "org_repo": "acme/acmeflux-python",
        "facts": [
            {
                "fact_id": "product.identity:manifest-and-registry",
                "field": "product.identity",
                "value": {
                    "family": "acmeflux",
                    "platform": "python",
                    "ecosystem": "python",
                    "repository": "acme/acmeflux-python",
                    "manifest_names": ["acmeflux"],
                },
            },
            {
                "fact_id": "product.platforms:manifest",
                "field": "product.platforms",
                "value": ["python"],
            },
            {
                "fact_id": "product.license:license-file",
                "field": "product.license",
                "value": "MIT",
            },
        ],
    },
    indent=2,
)
PYTHON_CONTEXT_FILES = {
    "README.md": (
        "# AcmeFlux\n\nAcmeFlux is a small Python library for validating CSV files against a "
        "declared column schema before loading them into a pipeline. MIT licensed.\n"
    ),
    "src/acmeflux/validator.py": (
        "class SchemaValidator:\n"
        "    def __init__(self, columns: list[str]) -> None:\n        self.columns = columns\n\n"
        "    def validate(self, path: str) -> bool:\n        return True\n"
    ),
}
PYTHON_CONTEXT = "".join(f"--- {path} ---\n{text}\n" for path, text in PYTHON_CONTEXT_FILES.items())

SCENARIOS = {
    "java_well_resourced": {
        "org_repo": "acme/acmecells-java",
        "ecosystem": "java",
        "facts_json": JAVA_FACTS_JSON,
        "context": JAVA_CONTEXT,
        "known_fact_ids": _JAVA_FACT_IDS,
        "known_paths": set(JAVA_CONTEXT_FILES),
        "known_content": "\n".join(JAVA_CONTEXT_FILES.values()),
        "expected_language": "java",
    },
    "python_sparse_evidence": {
        "org_repo": "acme/acmeflux-python",
        "ecosystem": "python",
        "facts_json": PYTHON_FACTS_JSON,
        "context": PYTHON_CONTEXT,
        "known_fact_ids": _PYTHON_FACT_IDS,
        "known_paths": set(PYTHON_CONTEXT_FILES),
        "known_content": "\n".join(PYTHON_CONTEXT_FILES.values()),
        "expected_language": "python",
    },
}


def _score_response(raw_text: str, scenario: dict) -> dict:
    """Schema validity against the REAL `DraftProductTruthV1` model, plus faithfulness: every
    citation (supporting_fact_ids / evidence_paths / required_symbols) must resolve to something
    actually given, never fabricated. Mirrors the deterministic gates this response would really be
    routed through in production (`facts/interpretive_evidence.py`/`facts/policy_evidence.py`),
    without importing those modules here -- a lighter, probe-local approximation is enough to rank
    candidate models; the real gates are exercised for real by this taskcard's own unit/live tests,
    not by this throwaway characterization script."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0] if "```" in text else text
    try:
        parsed = json.loads(text)
    except Exception as e:  # noqa: BLE001
        return {"schema_valid": False, "why": f"json:{e}", "raw_response": raw_text}
    try:
        draft = DraftProductTruthV1.model_validate(parsed)
    except Exception as e:  # noqa: BLE001
        return {"schema_valid": False, "why": f"pydantic:{e}", "raw_response": raw_text}

    fabricated_fact_ids = [
        fid
        for claim in (draft.audience + draft.problems_solved)
        for fid in claim.supporting_fact_ids
        if fid not in scenario["known_fact_ids"]
    ]
    evidence_backed = [*draft.capabilities, *draft.formats, *draft.limitations]
    fabricated_paths = [
        path
        for fact in evidence_backed
        for path in fact.evidence_paths
        if path not in scenario["known_paths"]
    ]
    fabricated_paths += [
        path for path in draft.minimal_example.evidence_paths if path not in scenario["known_paths"]
    ]
    all_required_symbols = [
        symbol for fact in evidence_backed for symbol in fact.required_symbols
    ] + list(draft.minimal_example.required_symbols)
    fabricated_symbols = [
        symbol for symbol in all_required_symbols if symbol not in scenario["known_content"]
    ]
    language_correct = draft.minimal_example.language == scenario["expected_language"]

    faithful = not fabricated_fact_ids and not fabricated_paths and not fabricated_symbols
    return {
        "schema_valid": True,
        "faithful": faithful,
        "language_correct": language_correct,
        "fabricated_fact_ids": fabricated_fact_ids,
        "fabricated_evidence_paths": fabricated_paths,
        "fabricated_required_symbols": fabricated_symbols,
        "n_audience_claims": len(draft.audience),
        "n_problems_solved_claims": len(draft.problems_solved),
        "n_capabilities": len(draft.capabilities),
        "n_formats": len(draft.formats),
        "n_limitations": len(draft.limitations),
        "minimal_example_language": draft.minimal_example.language,
        "raw_response": raw_text,
    }


# --- 3. faithfulness test (2 scenarios x chat models) --------------------------
faithfulness: dict = {}
for model in chat_models:
    model_results = {}
    for scenario_name, scenario in SCENARIOS.items():
        messages = build_draft_product_truth_messages(
            scenario["org_repo"],
            scenario["ecosystem"],
            scenario["facts_json"],
            scenario["context"],
            "",
        )
        ok, out, dt, usage = chat(model, messages)
        scored = _score_response(out, scenario) if ok else {"schema_valid": False, "why": out[:300]}
        scored["ok"] = ok
        scored["prompt_tokens"] = usage.get("prompt_tokens")
        scored["completion_tokens"] = usage.get("completion_tokens")
        scored["latency_s"] = round(dt, 1)
        model_results[scenario_name] = scored
        print(
            f"[3] {model} / {scenario_name}: ok={ok} schema_valid={scored.get('schema_valid')} "
            f"faithful={scored.get('faithful')} lang_correct={scored.get('language_correct')} "
            f"completion_tokens={usage.get('completion_tokens')} {dt:.1f}s"
        )
    n = len(SCENARIOS)
    model_results["_summary"] = {
        "schema_valid_rate": sum(
            1 for k, v in model_results.items() if not k.startswith("_") and v.get("schema_valid")
        )
        / n,
        "faithful_rate": sum(
            1 for k, v in model_results.items() if not k.startswith("_") and v.get("faithful")
        )
        / n,
        "language_correct_rate": sum(
            1
            for k, v in model_results.items()
            if not k.startswith("_") and v.get("language_correct")
        )
        / n,
    }
    faithfulness[model] = model_results
results["probes"]["faithfulness"] = faithfulness

# --- 4. N=2 stability repeat, leading candidate only ----------------------------
STABILITY_TRIALS = 2
stability: dict = {}
leading_candidate = (
    "qwen3-next" if "qwen3-next" in chat_models else (chat_models[0] if chat_models else None)
)
if leading_candidate:
    for scenario_name, scenario in SCENARIOS.items():
        outcomes = []
        messages = build_draft_product_truth_messages(
            scenario["org_repo"],
            scenario["ecosystem"],
            scenario["facts_json"],
            scenario["context"],
            "",
        )
        for i in range(STABILITY_TRIALS):
            ok, out, dt, usage = chat(leading_candidate, messages)
            scored = _score_response(out, scenario) if ok else {"schema_valid": False}
            outcomes.append(
                {
                    "trial": i + 1,
                    "ok": ok,
                    "schema_valid": scored.get("schema_valid"),
                    "faithful": scored.get("faithful"),
                    "language_correct": scored.get("language_correct"),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "latency_s": round(dt, 1),
                }
            )
            print(
                f"[4] {leading_candidate} / {scenario_name} trial {i + 1}/{STABILITY_TRIALS}: "
                f"schema_valid={scored.get('schema_valid')} faithful={scored.get('faithful')} "
                f"{dt:.1f}s"
            )
        stability[f"{leading_candidate}/{scenario_name}"] = {
            "trials": STABILITY_TRIALS,
            "schema_valid_rate": sum(bool(o["schema_valid"]) for o in outcomes) / STABILITY_TRIALS,
            "faithful_rate": sum(bool(o["faithful"]) for o in outcomes) / STABILITY_TRIALS,
            "outcomes": outcomes,
        }
results["probes"]["stability"] = stability

# --- write redacted evidence -------------------------------------------------
raw = json.dumps(results, indent=2)
(OUT_DIR / "probe-results.json").write_text(redact(raw), encoding="utf-8")
print(f"\nwrote: {(OUT_DIR / 'probe-results.json').relative_to(REPO_ROOT)}")
