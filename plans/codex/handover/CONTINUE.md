# Claude Start Here

Read these files in order before taking action:

1. `AGENTS.md`
2. `plans/codex/handover/HANDOVER.md`
3. `plans/codex/handover/state.json`
4. `plans/codex/handover/CLAUDE_GOAL.md`
5. `plans/codex/handover/CLAUDE_LOOP.md`
6. the authoritative files named in `HANDOVER.md` section 3

The human should paste `CLAUDE_GOAL.md` into Claude's `/goal`, then paste
`CLAUDE_LOOP.md` into `/loop`. Until that activation, this repository is at a stopped handover
checkpoint.

The first implementation action is not a new README or a non-Python task. Verify live Git and
mission status, reconcile and claim `L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES` if it remains the
printed task, then repair the PDF current-dependency acceptance-chain mismatch documented in:

`runs/multi-agent/L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES/independent-current/receipt.json`

Never treat this continuation pointer as plan or state authority.
