# Continue the Verified Portfolio Delivery Mission

Work in `D:\\Users\\prora\\OneDrive\\Documents\\GitHub\\foss-readme-optimizer`. The ultimate goal is a current, publication-ready, effect-neutral README POC: 31/31 processable repositories independently accepted at 30/30, immediate no-op-proven, PR_ELIGIBLE with valid proposal packets; two current source-empty PSD dispositions; terminal `PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION`; zero product effects.

Read completely before acting:

1. `AGENTS.md`
2. `plans/codex/handover/HANDOVER.md`
3. `C:\\Users\\prora\\.codex\\attachments\\a1a147bb-62fd-456b-94db-b799adcede5e\\goal-objective.md`
4. `plans/idea.md`, `plans/master.md`, `plans/requirements.md`, and `plans/requirements/catalog.jsonl`
5. `plans/investigations/control/level8-autonomous-mission-task-graph.yaml`

Live authority overrides this document. Before edits run:

```powershell
git status --short --branch
git log -1 --format=fuller
.venv/Scripts/readme-agent supervise `
  --mission-task-graph plans/investigations/control/level8-autonomous-mission-task-graph.yaml `
  --mission-action status `
  --mission-observer <agent-id> `
  --execution-profile local_poc
```

Inspect repository-owned processes. Never overlap a live repository transaction or steal a live unexpired claim. If status reports graph drift, a stale lease, or no eligible task while a task is inconsistent, run `--mission-action evaluate`; then claim only the task printed by the controller.

The intended current branch baseline is `main` at `8539afe6b`, with PF02/PF03/PF04 closed and `L8-PF-05-SEVEN-ECOSYSTEM-CANARIES` active. Treat this as historical until verified. The current accepted/no-op result is only Aspose.3D Python. Do not call historical raw lifecycle counts delivery.

`PF05-CXX-LINK-001` is resolved and canary-confirmed (`e2db75462`) -- do not re-fix it. The
`development_commands` claim-accountability gap behind it is also resolved (`8cb2a6cd8`,
`8539afe6b`): the C++ canary's blocking claims went 2 to 0 and both now resolve as
`verified_obligation_replacement`.

First task after safe claim: resolve `PF05-CXX-DUPLICATE-001`.

- Canary: `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp`, revision `9f852d0ff1cfdad2d661556d6b87a8eff8c063a2`.
- Current terminal failure: `presentation.semantic_duplicate.7f247683b2ff` and
  `public_quality.malformed_low_information_prose.6bec24bc9114` both report "Capability
  information is repeated across competing visitor sections", plus a
  `public_quality.contradiction_capability_symbol` finding on `DateTime`.
- The `DateTime` finding is already root-caused and logged as `CORE-038`: the vendored C++
  empty-body-stub detector does not recognize a constructor whose work lives in its
  member-initializer list, so it emits a false "unimplemented stub" limitation claim. Verified
  against the real upstream `Aspose.Cells.Foss.Cpp/src/DateTime.cpp:77`. Do not patch it inside
  the byte-integrity-checked vendored tree -- see
  `plans/investigations/evidence/portfolio-proof-pf05-seven-ecosystem-canaries/cxx-datetime-stub-false-positive-2026-08-25.md`.
- Read the regenerated candidate and its `blocked-presentation-plan.json` before changing shared
  composition code; the duplicate-capability findings have not yet been root-caused.

Note on the approach budget: a claim that expires mid-canary is recorded as an *ineffective*
attempt, so two lease expiries alone exhaust the budget and the controller will refuse the task
until a first-principles replan is recorded. Long canaries should be started with a fresh claim.

Then follow this exact loop:

```text
verify authority/live state
→ claim highest-priority eligible graph task
→ implement the smallest complete causal repair
→ focused test and directly affected safety/integration proof
→ affected real canary
→ independent verification
→ repair the first failing boundary
→ retain checksum-complete evidence and valid caches
→ transition the same task only with current proof
→ commit coherent code directly to main
→ evaluate/rebuild eligibility
→ continue
```

PF05 order is fixed: complete all seven first-boundary receipts, causal reduction, one shared repair per evidence-backed cluster, failed-only reruns, then 30/30/no-op seal. PF06 is read-only discovery/fact warmup; it must not generate candidates. Only after PF05 and PF06 can the portfolio fan-out run. PF07 produces effect-neutral publication packets only. No product remote effect is authorized.

Anti-waste rules:

- Do not create a competing plan/controller/lifecycle/graph/template/evidence system.
- Do not run full pytest after every repair. Use the optimized full non-live runner only at coherent task/portfolio boundaries.
- Reuse unchanged snapshots, facts, Qwen sections, review packets, and provider calls.
- After two equivalent failures or 15 minutes without narrowing, record a first-principles replan and change approach.
- Keep shared code/state/commits under one coordinator. Enable at most two disjoint workers only after PF05 isolation proof.
- Preserve dirty or user-owned work; never reset/restore/clean/force-push.
- Commit Codex work with `Co-Authored-By: Codex <noreply@openai.com>`.

The mission may stop only when every required outcome above is proven or all remaining work is blocked by genuine unavailable external authority. Test failure, expired lease, dirty tree, cache miss, coding defect, model output, or incomplete evidence is agent-fixable and does not end the mission.
