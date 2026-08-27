"""One-shot retrofit: append Decisions #109-113 (2026-08-27 production recovery sprint) to
`plans/decisions/catalog.jsonl`, matching the existing per-record convention (`markdown` field =
"N. **Title.** body", `legacy_record_sha256` = sha256(markdown)). See
`plans/investigations/production-recovery-sprint-2026-08-27.md` for the full investigation these
decisions come from, and `plans/master.md`'s Decision Ledger for their human-readable prose.

Kept after use as the executable record of how these five catalog rows were produced, per this
repo's retrofit-script convention (GOVERNANCE.md rule 8).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "plans" / "decisions" / "catalog.jsonl"

DECISIONS: list[tuple[int, str, str]] = [
    (
        109,
        "Pinned-content-hash consistency is mechanically enforced, never hand-remembered.",
        "109. **Pinned-content-hash consistency is mechanically enforced, never hand-remembered.** "
        "Every place this codebase pins a recorded hash/count against recomputed source truth (the "
        "composition document-template hash, the vendored Aspose.org check-battery manifest, "
        "`PUBLIC_QUALITY_CHECKS_VERSION`, the composition-characterization test fixtures, "
        "`plans/requirements.md`'s own summary counts, and `validate_compact_authority.py`'s "
        "semantic-hash checks) is registered in one declarative checker run as its own fast, "
        "independent CI job, separate from the full pytest matrix, that fails loudly with the "
        "exact command to re-pin. This does not prevent a deliberate contract change from needing "
        "a human to re-pin it; it converts silent, days-old wrongness into next-commit loud "
        "wrongness. Proven need: the 2026-08-27 production recovery sprint found six live "
        "instances of exactly this drift, none a behavioral regression, all traceable to a real "
        "code change whose pin was never updated in the same commit.",
    ),
    (
        110,
        "Every LLM-authored judgment surface is ratcheted; none is exempt.",
        "110. **Every LLM-authored judgment surface is ratcheted; none is exempt.** The "
        "claim-disposition, bounded-review, section-authoring, and trusted-fidelity-review "
        "judgment surfaces already persist an accepted verdict keyed by content hash plus a "
        "deliberately-bumped contract-version literal, so a rerun with unchanged inputs reproduces "
        "the same verdict instead of re-rolling qwen3-next's proven-nondeterministic tool-call "
        "arguments (Decision #105). The prose-quality check is the one surviving surface with no "
        "such cache; it must gain one, keyed identically (content hash plus a new "
        "`PROSE_QUALITY_CONTRACT_VERSION` literal), before `L8-PF-03-SEALED-CANDIDATE-NO-OP`'s own "
        '"unchanged rerun performs zero new author/reviewer calls" acceptance check can be true in '
        "practice.",
    ),
    (
        111,
        "Composition-plan reuse invalidation is scoped to actual per-repository dependency, never "
        "one global content hash.",
        "111. **Composition-plan reuse invalidation is scoped to actual per-repository dependency, "
        "never one global content hash.** `document_template_hash()`'s current single glob-wide "
        "digest over ~50 files plus four broad patterns invalidates every repository's cached plan "
        "on any byte changed anywhere in that surface, regardless of whether a given repository's "
        'own composition depends on the changed path -- the proven mechanism behind "a fix cannot '
        'land mid-fleet-pass without invalidating every cached plan." The reuse gate must instead '
        "hash the recorded, actually-exercised per-repository dependency set (mirroring "
        "`ProvenTransactionContextV1.dependency_hashes`'s existing precedent of hashing what is "
        "actually exercised, not a static glob); the current global hash remains as a non-blocking "
        "provenance/era label and the trigger for periodic full-fleet re-validation at declared "
        "campaign boundaries, finishing what Decision #90's \"component deltas rather than global "
        'invalidation" language already commits to. Cutover follows a shadow period -- dual-hash '
        "logging for at least one full portfolio pass, reviewed before the reuse decision itself "
        "switches -- because under-invalidation is worse than over-invalidation.",
    ),
    (
        112,
        "Convergence-critical ratchet state is durable and portfolio-shared, never disposable "
        "local-only state.",
        "112. **Convergence-critical ratchet state is durable and portfolio-shared, never "
        "disposable local-only state.** The claim-disposition ratchet and blocked-decision cache "
        "are not derived output; they are the accumulated, validated record of which "
        "nondeterministic model answers this project has already stood behind, and today live only "
        "under gitignored `runs/`, restored by nothing (confirmed: zero `actions/cache` usage in "
        "any workflow). They must route through the same `GitStateBackend` mission state already "
        "uses, under their own key namespace, batched per repository-pass, with a CAS-write "
        "failure treated as non-fatal (log, retry next pass) rather than blocking a candidate. "
        "This does not by itself resolve two machines' literal first concurrent encounter with a "
        "brand-new claim (Decision #113 protects that frontier); it ensures an accepted verdict "
        "becomes visible to every other machine/CI run the first time anyone accepts it, instead "
        "of only to whichever machine happened to. Requires a load-characterization pass at full "
        "fleet scale before fleet-wide reliance.",
    ),
    (
        113,
        "CAS post-push-failure classification is hardened as defense-in-depth, with confidence "
        "stated honestly.",
        "113. **CAS post-push-failure classification is hardened as defense-in-depth, with "
        "confidence stated honestly.** `_is_non_fast_forward()` classifies a push failure by "
        "matching hardcoded stderr substrings; on any push failure the backend should instead "
        "re-fetch and structurally re-compare state_version/SHA before deciding stale vs. "
        "hard-error, rather than trusting failure-text matching alone -- necessary regardless of "
        "root cause once Decision #112 adds more traffic through this exact path. A direct "
        "2026-08-27 probe against a local bare remote did **not** reproduce the originally "
        'reported "raw git push rejection" (the existing same-ref concurrency test passed 6/6 '
        "local runs, and a manual non-fast-forward push against a custom "
        "`refs/readme-agent-state/*` ref classified correctly 1/1 times); that symptom is better "
        "explained by `test_state_git_backend_live.py` needing real GitHub credentials this "
        'environment likely lacked, not a proven classifier defect. The CI "both saved" anomaly '
        "from the original report remains unreproduced and unexplained -- recorded as an open "
        "unknown, not force-fit into this decision's justification.",
    ),
]


def main() -> None:
    existing_ids = set()
    if CATALOG_PATH.exists():
        for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing_ids.add(json.loads(line)["decision_id"])
    new_rows = []
    for decision_id, title, markdown in DECISIONS:
        if decision_id in existing_ids:
            print(f"skip: decision {decision_id} already present")
            continue
        new_rows.append(
            json.dumps(
                {
                    "decision_id": decision_id,
                    "legacy_record_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
                    "markdown": markdown,
                    "schema_version": 1,
                    "title": title,
                },
                ensure_ascii=False,
            )
        )
    if not new_rows:
        print("nothing to append")
        return
    with CATALOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
        for row in new_rows:
            f.write(row + "\n")
    print(f"appended {len(new_rows)} decision record(s) to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
