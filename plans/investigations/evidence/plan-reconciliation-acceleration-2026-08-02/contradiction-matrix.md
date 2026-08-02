# Plan Reconciliation Contradiction Matrix

Snapshot base: control branch `main`, commit
`59b94b9ecc089c3dca96856077559a4efca35566`. The working-tree amendments are the
candidate being validated; durable mission state remains the live status authority.

| ID | File and section | Conflict | Selected rule and amendment | Migration impact |
|---|---|---|---|---|
| AUTH-01 | `AGENTS.md`; `plans/GOVERNANCE.md`; `plans/idea.md`; `plans/master.md`; supporting Codex plan | Files described `master.md`, a linear list, or the graph as universal authority. | Apply one subject-specific authority matrix: idea=outcome, requirements=acceptance, master=architecture/sequence, governance=safety/editing, graph=tasks/dependencies, durable state=live status, other plans/reports=derived. | Documentation and validators resolve conflicts by subject; live state is not rewritten from prose. |
| TRUST-01 | `plans/idea.md`; decisions #85/#88; `AGENTS.md`; governance rules 15/18 | Trusted execution was both suspended and described as primary/critical. | Keep every trusted goal non-executable, zero-capacity, and effect-disabled. Retain assets and evidence only behind verified contracts. | Trusted statuses/history remain inspectable but cannot be selected or satisfy/block verified closure. |
| TRUST-02 | `plans/requirements.md` `TRP-*`; graph mandatory criteria and goal catalog | Open trusted-only requirements and T2/T3 outcomes remained mandatory despite disabled goals. | Mark unfinished trusted-only rows `DEPRECATED`; remove trusted outcomes from active mandatory criteria; preserve anti-promotion and reusable obligations under active L8/NFR/VER requirements. | No false `IMPLEMENTED` status; no trusted evidence is relabelled as verified. |
| TRUST-03 | Graph task mappings | Shared `L8-MISSION-*`, Wave 0-2, and preproduction tasks were assigned to the disabled trusted T0 goal. | Move governance/control tasks to P0, verified truth/safety tasks to V1, and workflow/staging tasks to V3. Leave only `TRP-*` taskcards under historical goals. | Durable task IDs and transition history are preserved; only campaign ownership changes. |
| SEQ-01 | idea milestone; master decisions #82/#83/#88; `AGENTS.md`; supporting Codex plan; roadmap | Note/Page/PDF-first, trusted-first, seven-first, and Note/.NET/Java-first sequences coexisted. | Use exactly: plan freeze; state migration; dependency freeze; zero-call .NET/Java readiness; Note no-op; parallel .NET/Java slices; three approvals/no-ops; suite; Page/PDF; all Python; later platforms; Gates A/B/C; Levels 5-8. | Existing valid receipts remain reusable only when their complete dependency keys match. |
| TASK-01 | `L8-VPY-02-PAGE-PDF-VERIFIED-CANARIES` | Durable ID said Page/PDF while the task performed .NET/Java slices. | Retain the ID as a compatibility identifier with canonical .NET/Java title/purpose; add `L8-VPY-03A-PAGE-PDF-VERIFIED-CANARIES` as the separate Python boundary. | Additive graph migration; old ID/history remain valid and unambiguous. |
| CONC-01 | decisions #82/#83; `SCL-002`; `L8-016/017/043`; graph goal schema | Seven representatives were both a serial fan-out prerequisite and only a coverage milestone; concurrency field was trusted-specific. | Permit up to three isolated early slice lanes, then two-to-four lanes after three-slice proof. Seven ecosystems remain qualification coverage. Rename goal concurrency to `concurrent_when_earlier_primary`. | P0 has zero lanes; V0 may admit ready C0/V1/V2 read-only work; aggregation remains serialized. |
| STATUS-01 | `plans/status.md`; traceability generator | Generated status used a stale 32-entry historical manifest containing an excluded MCP repository. | Derive current counts from the live 31-entry registry, durable lifecycle state, current fact/acceptance contracts, and current registry-revision gate; report raw legacy reach separately. | Historical manifests remain evidence but cannot supply headline completion. Missing current sources fail closed. |
| STATE-01 | Graph `status` fields versus durable state v690 | Static bootstrap values contradicted the live Note claim. | Graph status is explicitly bootstrap/default metadata; durable state is the sole live claim/transition/status authority. Status rendering overlays durable state and reports graph drift. | `evaluate` adds new IDs, updates the graph hash, and recovers only an expired claim; it never deletes history. |
| REVIEW-01 | decision #87; `NFR-012`; `VER-011`; reviewer task family | Universal duplicate independent review consumed high provider time while deterministic gates and roles overlapped. | Require one independent non-authoring evidence-grounded reviewer for every candidate; add a second only for a typed `ReviewRiskProfileV1` condition. Do not remove universal dual review until the merged reviewer passes the frozen regression corpus. | Existing reviewer evidence remains historical; failing risk classes retain targeted second review. |
| CONTRACT-01 | master Validator Registry and LLM Contract | Sections described the early ten-rule/one-job renderer, not the verified pipeline. | Replace them with layered factuality/preservation/presentation/link/legal/lifecycle gates and governed composition/review/repair jobs with per-job budgets and ledgering. | Contract hashes become `CampaignFreezeV1` dependencies; current implementation remains partial until qualified. |
| TIME-01 | Build/verification checklists; requirements; graph tasks | One-day/seven-representative and 7-12-day targets conflicted with measured acceleration targets. | Use stretch SLOs: plan <=60 focused minutes; three slices <=3 active hours; Python <=6 active hours; Gate A one measured bounded window. A breach repairs the first measured boundary. | Targets never substitute for acceptance or authorize scope reduction. |
| CAMPAIGN-01 | Graph micro-task execution and repeated verification prose | Each micro-task could trigger separate full suites, evidence ZIPs, commits, and reviews. | Add a typed six-item `campaign_catalog`, require exactly one campaign for every executable task, propagate `campaign_id` into next-task and contribution evidence, and enforce campaign equality at closeout. Only `CLOSED` still satisfies dependencies. | Campaigns are scheduling/evidence aggregation, not a second controller or status model. |
| ROADMAP-01 | `plans/roadmap.md` | A superseded banner was followed by executable-looking stale checklists and order. | Replace the body with a compact derived six-campaign view and explicit live-state lookup. | Git history preserves the old checklist; roadmap cannot direct execution. |

## Supporting audit evidence

- `runs/multi-agent/PLAN-RECONCILIATION-ACCELERATION-2026-08-02/authority-trusted-sequence/report.md`
  (`sha256:5701efea51e8fb61afa9127430c94f2bf0b1af41b8fcd9b7462f0d27ae49c66b`)
- `runs/multi-agent/PLAN-RECONCILIATION-ACCELERATION-2026-08-02/graph-status-runtime/report.md`
  (`sha256:36e1a871adc08a29df5a51805f15e05d13d0e507d097a86ba5c1a42bf25b6c4d`)
- `runs/multi-agent/PLAN-RECONCILIATION-ACCELERATION-2026-08-02/reviewer-llm-campaign/report.md`
  (`sha256:921b698420142bb2f289760d6695cc7d182c948c5ad09786cd9524f6368c0de0`)

## Independent-review repair history

The first independent candidate review returned `PRE_FREEZE_REJECTED`. It found universal dual-review
taskcards, seven-first and stale timing language, prose-only campaigns, an extra Python full-suite
gate, and overclaimed evidence. The coordinator repaired those causal owners in the graph, schema,
mission control, requirements, master status/checklist, and evidence rather than waiving them. The
same non-authoring lane must re-review the current candidate before `CampaignFreezeV1` is allowed.
