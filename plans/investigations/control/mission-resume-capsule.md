# Mission resume capsule (derived — regenerate, never hand-edit)

Regenerated: 2026-08-18T18:34:53+00:00
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

- branch `main` @ `299b0355070014a43e8799b135b35806d3e51996`
- protected pre-existing dirt: `plans/requirements.md` (CRLF-only); untracked
  `plans/claude/moonlit-juggling-flurry.md` is `forbidden_paths` reference material.

## Durable mission state (local store)

- `mission__LEVEL8-CENTRAL-REPOSITORY-PRESENTATION` — state: mission/LEVEL8-CENTRAL-REPOSITORY-PRESENTATION v2 (2026-08-18T21:54:50+05:00)
- newest state ref write: 2026-08-18T23:30:24+05:00

## Portfolio (from `runs/readme-poc/portfolio-summary.json`)

- generated_at: 2026-08-18T18:14:20.523398+00:00  (registry_count=33, slice_complete=False)
- statuses in last slice: AGENT_APPROVED=3, BLOCKED_MISSING_EVIDENCE=2, FACTS_READY=6
- blocked members (last slice):
  - aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 2 blocking cl
  - aspose-email-foss/Aspose.Email-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 1 blocking cl
  - aspose-font-foss/Aspose.Font-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 3 blocking cl
  - aspose-html-foss/Aspose.HTML-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE
  - aspose-note-foss/Aspose.Note-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 1 blocking cl
  - aspose-page-foss/Aspose.Page-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountability has 1 blocking cl
  - aspose-psd-foss/Aspose.PSD-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE
  - aspose-slides-foss/Aspose.Slides-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['unauthorized protected-content loss: t

## Cached decisions

- blocked-decision records (skip-cached until a dependency changes):
  - aspose-3d-foss/Aspose.3D-FOSS-for-.NET: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=1)
  - aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=2)
  - aspose-email-foss/Aspose.Email-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=2)
  - aspose-font-foss/Aspose.Font-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=2)
  - aspose-html-foss/Aspose.HTML-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE (live_reproductions=2)
  - aspose-note-foss/Aspose.Note-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=1)
  - aspose-page-foss/Aspose.Page-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=1)
  - aspose-psd-foss/Aspose.PSD-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE (live_reproductions=1)
  - aspose-slides-foss/Aspose.Slides-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['unauthorized prote (live_reproductions=1)
  - aspose-tex-foss/Aspose.TeX-FOSS-for-Python: product_truth_not_ready:BLOCKED_MISSING_EVIDENCE (live_reproductions=1)
  - aspose-words-foss/Aspose.Words-FOSS-for-Python: specialist_failed:readme_presentation:ERROR:presentation_plan:blocked:['claim accountabili (live_reproductions=1)
- claim-disposition ratchets:
  - aspose-3d-foss__Aspose.3D-FOSS-for-.NET: 5 accepted verdict(s)
  - aspose-cells-foss__Aspose.Cells-FOSS-for-.NET: 15 accepted verdict(s)
  - aspose-email-foss__Aspose.Email-FOSS-for-Python: 1 accepted verdict(s)
  - aspose-font-foss__Aspose.Font-FOSS-for-Python: 1 accepted verdict(s)
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
