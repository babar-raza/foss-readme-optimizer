#!/usr/bin/env python3
"""One-shot: append the 5 new requirement rows (GOV-032, LLM-023, CORE-039, SAFE-020, SAFE-021) for
the 2026-08-27 production recovery sprint's Decisions #109-113. See
`plans/investigations/production-recovery-sprint-2026-08-27.md` for the investigation and
`plans/master.md`'s Decision Ledger for the ratified decision text these requirements enforce.

Run once from the repo root:
`.venv/Scripts/python scripts/retrofits/append_production_recovery_requirements.py`
Kept after use as the executable record of what was appended (repo layout placement rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "requirements" / "catalog.jsonl"

ROWS: list[dict] = [
    {
        "requirement_id": "GOV-032",
        "section": "3. Requirements governance",
        "status": "PLANNED",
        "priority": "P2",
        "requirement": (
            "Every place this codebase pins a recorded hash/count against recomputed source truth "
            "(the composition `document_template_hash()`, the vendored Aspose.org check-battery "
            "manifest, `PUBLIC_QUALITY_CHECKS_VERSION`, "
            "`test_readme_composition_characterization.py`'s fixture hashes, "
            "`plans/requirements.md`'s own summary counts, and `validate_compact_authority.py`'s "
            "semantic-hash checks) MUST be checked by one declarative registry run as its own "
            "fast, independent CI job (not nested in the full pytest matrix), printing the exact "
            "command to re-pin on mismatch."
        ),
        "acceptance_evidence": (
            "GOV032-PINNED-HASH-DRIFT-001 (2026-08-27, production recovery sprint): found 6 live "
            "instances of exactly this drift pattern -- 3 currently-failing CI tests "
            "(test_readme_composition_characterization.py, "
            "test_aspose_org_check_battery_source.py, test_public_candidate_quality_registry.py), "
            "plans/requirements.md's stale summary counts (497 vs. actual 509 at sprint start), "
            "and validate_compact_authority.py's own 6 pre-existing errors (not wired into CI at "
            "all -- confirmed via `grep -rn actions/cache .github/workflows/` = 0 hits and reading "
            ".github/workflows/ci.yml directly). None of the 6 is a behavioral regression; each is "
            "a real, verified code/data change whose recorded pin was never updated in the same "
            "commit. Decision #109."
        ),
        "traceability": "Decision #109; production-recovery-sprint-2026-08-27.md",
    },
    {
        "requirement_id": "LLM-023",
        "section": "11. LLM requirements",
        "status": "PLANNED",
        "priority": "P1",
        "requirement": (
            "The prose-quality judgment surface (`verify_prose_quality`, dispatched from "
            "`specialists/readme_presentation.py`) MUST persist an accepted verdict keyed on "
            "`sha256(final_text)` plus a new deliberately-bumped `PROSE_QUALITY_CONTRACT_VERSION` "
            "literal, matching the existing ratchet pattern already proven correct for claim "
            "disposition, bounded review, section authoring, and trusted-fidelity review, so a "
            "rerun with unchanged input text does not re-invoke the model."
        ),
        "acceptance_evidence": (
            "LLM023-PROSE-QUALITY-UNCACHED-001 (2026-08-27, production recovery sprint): direct "
            "code read of `specialists/readme_presentation.py:676-690` and "
            "`capabilities/dispatcher.py` found zero cache/memoization at this call site, versus "
            "confirmed fine-grained version-literal caching at the other four LLM judgment "
            "surfaces (`bounded_review_repairs.py:181-195`, `section_authoring_cache.py:52-84`, "
            "`trusted_fidelity_cache.py:19-61`, "
            "`claim_accountability_llm_disposition.py:188-246`). This is a hidden blocker of "
            "`L8-PF-03-SEALED-CANDIDATE-NO-OP`'s own acceptance check that an unchanged rerun "
            "performs zero new author/reviewer calls. Decision #110."
        ),
        "traceability": "Decision #110; production-recovery-sprint-2026-08-27.md",
    },
    {
        "requirement_id": "CORE-039",
        "section": "9. Core engine and registry requirements",
        "status": "PLANNED",
        "priority": "P1",
        "requirement": (
            "The composition-plan reuse gate MUST hash only the recorded, actually-exercised "
            "per-repository module dependency set, not `document_template_hash()`'s current single "
            "SHA-256 digest over ~50 named files plus 4 broad glob patterns "
            "(`presentation/verified_*.py`, `links/*.py`, `readme/claim_*.py`, "
            "`readme/source_claim_*.py`) computed once globally with no per-repository scoping. "
            "The existing global hash remains as a non-blocking provenance/era label and the "
            "trigger for a periodic full-fleet re-validation at declared campaign boundaries. "
            "Cutover from the current global hash MUST follow a shadow period of dual-hash logging "
            "for at least one full portfolio pass, reviewed before the reuse decision itself "
            "switches."
        ),
        "acceptance_evidence": (
            "CORE039-GLOBAL-INVALIDATION-BLAST-RADIUS-001 (2026-08-27, production recovery "
            "sprint): `document_template_hash()` read in full "
            "(`readme/document_templates.py:92-130`), confirmed embedded as `template_sha256` in "
            "every repository's persisted plan (`document_plan_finalizer.py:54`) and checked "
            "verbatim on replay (`document_validation.py:271`). Directly explains the 2026-08-26 "
            "RDM-029 log finding ('cannot be fixed mid-fleet-pass without invalidating every "
            "repository's cached composition plan') as a mechanical consequence of the hash's lack "
            "of per-repository scoping, not an incidental one-off. "
            "`ProvenTransactionContextV1.dependency_hashes` "
            "(`proven_transaction_runner/contracts.py:60-79`) already establishes the precedent of "
            "hashing what is actually exercised rather than a static glob, at the "
            "transaction-identity layer -- this requirement applies that same precedent one layer "
            "down, at the composition-plan reuse layer. Decision #111."
        ),
        "traceability": "Decision #111; production-recovery-sprint-2026-08-27.md",
    },
    {
        "requirement_id": "SAFE-020",
        "section": "13. Safety, security, and evidence requirements",
        "status": "PLANNED",
        "priority": "P1",
        "requirement": (
            "The claim-disposition ratchet and blocked-decision cache MUST route through the same "
            "`GitStateBackend` mission state already uses, under their own key namespace, batched "
            "per repository-pass, instead of the current plain local JSON files under gitignored "
            "`runs/` (confirmed portable to no fresh clone/CI run: zero `actions/cache` usage in "
            "any workflow, zero tracked seed data under `plans/`/`data/`). A CAS-write failure for "
            "a ratchet entry MUST be treated as non-fatal (logged, retried next pass), never "
            "blocking a candidate. Requires a load-characterization pass at full 34-repository "
            "fleet scale before fleet-wide reliance."
        ),
        "acceptance_evidence": (
            "SAFE020-RATCHET-STATE-NOT-PORTABLE-001 (2026-08-27, production recovery sprint): "
            "confirmed via `git check-ignore -v` on `runs/local-poc-state/state.git` and a "
            "per-repo `claim-disposition-ratchet.json`, plus `git ls-files | grep '^runs/'` "
            "returning 0 results. Traced the concrete divergence risk in "
            "`llm_verified_claim_disposition()` "
            "(`claim_accountability_llm_disposition.py:155-270`): two machines racing the "
            "identical first-ever live call for the same claim-content-hash can receive two "
            "different nondeterministic model quotes (Decision #105's proven tool-call "
            "nondeterminism), one corroborating and one not, and the "
            "accept-only-persists-by-design ratchet then entrenches each machine's own answer "
            "permanently with no reconciliation channel. Decision #112."
        ),
        "traceability": "Decision #112; production-recovery-sprint-2026-08-27.md",
    },
    {
        "requirement_id": "SAFE-021",
        "section": "13. Safety, security, and evidence requirements",
        "status": "PLANNED",
        "priority": "P2",
        "requirement": (
            "On any Git-backend CAS push failure, `GitStateBackend.save()` SHOULD re-fetch the "
            "remote ref and structurally re-compare state_version/SHA before deciding `stale` vs. "
            "raising `StateBackendError`, rather than relying solely on `_is_non_fast_forward()`'s "
            "hardcoded stderr substring matching, as defense-in-depth against "
            "git-version/locale-dependent wording changes."
        ),
        "acceptance_evidence": (
            "SAFE021-CAS-CLASSIFIER-HARDENING-DEFENSE-IN-DEPTH-001 (2026-08-27, production "
            "recovery sprint): a direct probe against a throwaway local bare remote found the "
            "originally reported failure mode did NOT reproduce -- the existing same-ref "
            "concurrency test in `tests/integration/test_state_git_backend_local_parallel.py` "
            "(`test_separate_process_workspaces_preserve_same_ref_cas`) "
            "passed 6/6 consecutive local runs, and a manual non-fast-forward push against a "
            "custom `refs/readme-agent-state/*` ref classified correctly as `stale` on 1/1 "
            "attempts. The originally reported symptom is better explained by "
            "`tests/integration/test_state_git_backend_live.py` (marked `@pytest.mark.live`) "
            "needing real GitHub credentials this environment likely lacked, not a proven "
            "classifier defect -- downgraded from P1/proven-root-cause to P2/prudent-hardening "
            "accordingly. The CI 'both writers saved' anomaly from the original report remains "
            "unreproduced and unexplained; recorded as an open unknown, not resolved by this "
            "requirement. Decision #113."
        ),
        "traceability": "Decision #113; production-recovery-sprint-2026-08-27.md",
    },
]


def _synthetic_hash(marker: str) -> str:
    return hashlib.sha256(f"native-authored:{marker}".encode()).hexdigest()


def main() -> None:
    lines = CATALOG_PATH.read_text(encoding="utf-8").splitlines()
    existing = {json.loads(line)["requirement_id"] for line in lines if line.strip()}
    new_rows = [row for row in ROWS if row["requirement_id"] not in existing]
    if not new_rows:
        print("no new rows to append (already present)")
        return
    for row in new_rows:
        record = {
            **row,
            "schema_version": 1,
            "legacy_line": len(lines) + 1,
            "legacy_row_sha256": _synthetic_hash(row["requirement_id"]),
        }
        lines.append(json.dumps(record, ensure_ascii=False))
    CATALOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"appended {len(new_rows)} requirement rows to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
