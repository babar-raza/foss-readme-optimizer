# Mission resume capsule (derived — regenerate, never hand-edit)

Regenerated: 2026-08-18T17:08:23+00:00
Rebuild: `.venv/Scripts/python scripts/governance/mission_resume_capsule.py`
Staleness check (run at session start; exit 1 = stale): same command with `--check`.

## Mission

Deliver the complete local README candidate portfolio at Aspose.org quality parity
(`L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY`, lane readme-portfolio-delivery), using
`qwen3-next` via `https://llm.professionalize.com/v1` (exact provider id, live-confirmed; no
`qwen2-next` exists). Local only: no push, no PR, no target-repository writes. Aspose.org at
`D:/onedrive/Documents/GitHub/aspose.org` is a read-only behavioral reference (closure trace in
`plans/investigations/evidence/mission-recovery-2026-08-18/`).

## Non-goals

Remote writes of any kind; another blind portfolio loop over unchanged inputs; lowering
factuality/preservation/grounding gates to raise pass counts.

## Authoritative sources (read these, in order, before acting)

1. `plans/investigations/evidence/mission-recovery-2026-08-18/live-state-reconstruction.md`
2. `plans/investigations/evidence/mission-recovery-2026-08-18/failure-signature-ledger.md`
   (the engineering queue E1..E9 and signature clusters S1..S10)
3. `logs/2026-08-18.md` (tail) — what already landed, with commits
4. Durable state: `git --git-dir runs/local-poc-state/state.git for-each-ref`
5. `plans/master.md` Decision Ledger + `plans/GOVERNANCE.md` (process invariants)

## Repository

- branch `main` @ `9879f02ff2b4aba7a414a2d66ded5004c2afb21d`
- protected pre-existing dirt: `plans/requirements.md` (CRLF-only); untracked
  `plans/claude/moonlit-juggling-flurry.md` is `forbidden_paths` reference material.

## Durable mission state (local store)

- `mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` — state: mission/LEVEL8-CENTRAL-REPOSITORY-PRESENTATION v2 (2026-08-18T21:54:50+05:00)
- newest state ref write: 2026-08-18T22:05:13+05:00

## Portfolio (from `runs/readme-poc/portfolio-summary.json`)

- generated_at: 2026-08-18T15:04:38.215261+00:00  (registry_count=33, slice_complete=False)
- statuses in last slice: BLOCKED_MISSING_EVIDENCE=2, CANDIDATE_GENERATED=1, FACTS_READY=5, NO_OP_PROVEN=3
- blocked members (last slice):
  - aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 2 blocking cl
  - aspose-email-foss/Aspose.Email-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 1 blocking cl
  - aspose-font-foss/Aspose.Font-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 3 blocking cl
  - aspose-html-foss/Aspose.HTML-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE
  - aspose-note-foss/Aspose.Note-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 2 blocking cl
  - aspose-page-foss/Aspose.Page-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:factuality_rejected:claim_conflicts=0,protected_losses=1
  - aspose-psd-foss/Aspose.PSD-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE
  - aspose-slides-foss/Aspose.Slides-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['unauthorized protected-content loss: t

## Cached decisions

- claim-disposition ratchets:
  - aspose-note-foss__Aspose.Note-FOSS-for-Python: 2 accepted verdict(s)

## Resume commands

- Mission status (read-only): `./.venv/Scripts/python -m readme_agent.cli supervise
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml
  --mission-action status --execution-profile local_poc`
- Single-repo canary: `./.venv/Scripts/python -m readme_agent.cli supervise --repo <org/repo>
  --execution-profile local_poc --bounded-verified-canary
  --mission-task-id L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY
  --mission-observer readme-agent-supervisor`
- Portfolio pass: `bash scripts/retrofits/run_gate_a_local_poc_portfolio_loop.sh` (blocked
  members now skip via their dependency-bound blocked-decision records; `--retry-blocked`
  forces live re-runs).

## Publication boundary

Nothing leaves this machine. Candidates live under `runs/readme-poc/`; human review happens
locally. `GH_TOKEN` recipe and remote-write gates unchanged.
