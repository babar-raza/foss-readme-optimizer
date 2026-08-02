# Roadmap (derived campaign view)

This file is a supporting view, not execution authority. It must never be used to override:

- `plans/idea.md` for product outcome and operating intent;
- `plans/requirements.md` for obligations and acceptance;
- `plans/master.md` for architecture, decisions, sequencing, and rollout;
- `plans/GOVERNANCE.md` and `AGENTS.md` for safety, editing, execution, and coordination;
- `plans/investigations/control/level8-autonomous-mission-task-graph.yaml` for machine-readable
  tasks and dependencies; or
- durable supervisor state for live claims, transitions, and runtime status.

Regenerate or reconcile this view after every campaign transition. Static checkboxes here do not
close tasks and historical trusted work is not executable.

## Current campaign order

1. **Plan reconciliation and freeze**
   - Resolve the accepted contradiction inventory.
   - Migrate graph/state without deleting transition history.
   - Regenerate current status and freeze `CampaignFreezeV1`.
2. **Shared acceleration and isolation proof**
   - Freeze Note and campaign dependencies.
   - Run zero-provider-call .NET/Java readiness classification.
   - Qualify cache, invalidation, reviewer-risk, immutable-revision reuse, and lane isolation.
3. **Three verified vertical slices**
   - Complete fresh Note no-op proof.
   - Complete readiness-selected .NET and Java candidates in isolated lanes.
   - Independently approve and no-op-prove all three, then run one official integration suite.
4. **Verified Python portfolio**
   - Complete Page and PDF first.
   - Complete every runtime-loaded Python repository while later-platform read-only preparation may
     continue in spare isolated capacity.
5. **Remaining verified Gate-A portfolio**
   - Continue candidate delivery through .NET, Java, C++, TypeScript, Rust, and Go.
   - Complete heterogeneous qualification and the dynamic full-registry Gate-A proof.
6. **Gate B and later governed gates**
   - Present the human review package only after deterministic and independent acceptance.
   - Continue Gate C, hosted GitHub App operation, all presentation surfaces, and Levels 5-8 in
     the governed order.

## Current sequence invariants

- `trusted_readme_transform` execution is suspended. Its compatible machinery and evidence remain
  reusable only behind verified contracts and never satisfy verified acceptance.
- Python is the first complete platform milestone; ready read-only work for later platforms need
  not remain idle.
- Up to three isolated lanes are allowed for the early Note/.NET/Java proof. After those slices
  pass, use two to four isolated repository lanes with serialized aggregate state.
- The seven-ecosystem set is a heterogeneous coverage milestone, not an admission prerequisite for
  early slices, Python work, or later-platform read-only preparation.
- The official complete non-live suite runs at three-slice closure and Gate-A closure, plus only a
  declared later repository-wide gate or typed P0 exception.
- No product repository write, branch, push, or pull request is authorized by this roadmap.

## Live status

Read `plans/status.md` for the generated current portfolio and mission view. On every restart run
the canonical supervisor mission `status`; if graph drift is reported, reconcile through
`evaluate` and the recorded migration rather than treating this file as state.
