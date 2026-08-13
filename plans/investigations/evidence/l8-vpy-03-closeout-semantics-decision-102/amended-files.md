# Amended File Inventory — L8-VPY-03 closeout-semantics amendment (governance decision 102)

Snapshot base: `main` at `bf9b3e0688213a95e79fe9df656b86659d9494ef`.

## Owning plans and governance

- `plans/master.md` — Decision Ledger gains a short summary bullet for decision 102; the ledger's
  own "N stable decisions" header line updated 101 -> 102 (an independent-review finding, fixed).
- `plans/decisions/catalog.jsonl` — full canonical text of decision 102 appended (`decision_id: 102`).
- `report/findings/psd/python/upstream-issues.md` — new dedicated disposition record for PSD
  (owner, evidence, resume predicate), added after independent review found PSD had no structured
  record comparable to HTML's/TeX's (an independent-review finding, fixed).
- `logs/2026-08-13.md` (new shard) and `logs/README.md` — dated narrative entry and shard-index
  row for this amendment, including the GOV-032 attempt-and-revert below.
- `plans/requirements.md` and `plans/requirements/catalog.jsonl` — **attempted and reverted**: see
  "Reverted attempt" below. Both are byte-identical to the pre-session committed state.

## Executable graph

- `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` —
  `L8-VPY-03-ALL-PYTHON-VERIFIED-POC`'s `acceptance_checks` (first bullet), `closeout_rules`, and
  one `failure_reroute` clause amended in place to require `NO_OP_PROVEN` OR an accepted typed
  external-blocker disposition (decisions 101/102), instead of an unqualified "every repository
  ... no-op-proven". No other task's fields touched. `requirement_catalog` and
  `requirement_coverage` references are byte-identical to the pre-session committed values (see
  "Reverted attempt" below).

## Reverted attempt: GOV-032

A `GOV-032` `BACKLOG` row was initially added to `plans/requirements/catalog.jsonl`, flagging that
`plans/investigations/evidence/l8-vpy-03-python-external-blockers/README.md` is stale (2
blockers/12-repo denominator vs. the current true 3 blockers/13-repo state). A full pytest run
then surfaced 5 real, newly-broken `TestCompactAuthoritySourceBinding` failures:
`scripts/governance/validate_compact_authority.py`'s `_source_catalog_errors()` filters decisions
by `if record["decision_id"] in source_decision_ids` (why decision 102 caused zero failures) but
has no analogous filter for requirements — it does a strict full-list reconstruction match against
the original migration commit, so any new requirement row breaks it regardless of content. This is
a genuine, pre-existing gap in that validator (requirements cannot currently be appended
post-migration the way decisions can), not something this narrow amendment should also fix. The
`GOV-032` row, the `requirements.md` count edits, and the resulting graph-hash-reference changes
were fully reverted; `plans/requirements/catalog.jsonl`, `plans/requirements.md`, and
`plans/investigations/control/level8-deferred-task-catalog.jsonl` are byte-identical to the
pre-session committed HEAD (`git diff --stat` empty for all three). The underlying finding is
preserved as the new PSD disposition record above plus this note, instead of a formal catalog row
the current machinery cannot yet accept.

## Evidence produced by this amendment (this directory)

- `mission-graph-migration-v1.json` — before/after state-version and graph-hash receipt.
- `amended-files.md` — this file.
- `closeout-semantics-amendment-report.md` — narrative: why, what changed, what did not change,
  explicit scope limits.
- `static-and-focused-verification.json` — fresh `ruff check`, `ruff format --check`, `mypy src`,
  plan-structure validator, and complete non-live pytest suite results bound to this session's
  HEAD, plus the multi-agent execution-plan admission decision.
- `mission-contribution.json` / `closeout-control.json` — the actual
  `MissionContributionEvidenceV1` / `TaskCloseoutControlEvidenceV1` submitted to
  `readme-agent supervise --mission-action transition` to move `L8-VPY-03` through
  `IN_PROGRESS -> IMPLEMENTED -> VERIFIED -> SCORED -> CLOSED`.

## Explicitly excluded from this amendment

No product-repository write occurred. No repository's own `NO_OP_PROVEN` / working-condition-
exception / deferred / excluded disposition changed — HTML, PSD, and TeX remain exactly as
disposed on 2026-08-12 (see `logs/2026-08-12.md`). No other mission task's `closeout_rules`,
`acceptance_checks`, `dependencies`, or status changed. `plans/backlog-post-poc.md` (pre-existing,
user-owned, uncommitted) was not read for content beyond confirming it stayed untouched.
