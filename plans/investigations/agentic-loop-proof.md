# Agentic Loop Proof — Wave 1

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: `tools/prove_agentic_loop.py` — live, one observe -> plan -> execute -> observe ->
> replan loop against the real `llm.professionalize.com` gateway (`qwen3-next`) and the real,
> allow-listed `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` pilot repository. Read-only throughout
> — no git writes, no pushes, no mutation of any kind.
> satisfies: `AGT-002` acceptance bar ("Supervisor loop test: observe→plan→execute→observe→replan
> proven end-to-end").

## What this proves, and what it doesn't

This is a **spike**, not the production supervisor (Wave 5) or the capability registry (Wave 2).
It proves the loop *mechanics* work end to end against this specific weak gateway, using native
tool-calling (per `llm-gateway-characterization.md` findings L6/L7) as the structured-action
dispatch mechanism, with a throwaway 3-capability + 1-stop-signal menu wrapping already-existing,
already-proven, read-only functions:

- `inspect_repository` -> `orchestrator.inspect_repo(org_repo, check_install=False)`
- `detect_readme_gaps` -> `readme.gap_detector.detect()` (README text + detected license)
- `check_install_path` -> `orchestrator.inspect_repo(org_repo, check_install=True)` (live Maven
  Central resolution, opt-in, matches its existing never-a-default pattern)
- `stop_and_report` -> ends the loop; not a wrapped function, a pure control signal

It does not prove: cycle rejection, replanning *after a failure* (nothing failed in this run —
see "Deviations" below), durable state across a runner restart, multi-repository concurrency, or
repair-task creation. Those are Wave 2/4/5 territory and remain `PLANNED`.

## Live trace (4 rounds, full convergence)

| Round | Capability requested | Outcome | Real result |
|---|---|---|---|
| 1 | `inspect_repository` | executed | `has_readme=true`, `has_license_file=true`, `readme_length_chars=8074`, Maven manifest keys present |
| 2 | `detect_readme_gaps` | executed | `license_mentioned=true`, `products_org_link=**false**`, `products_com_link=true`, `relationship_explained=true`, `total_gaps=1` |
| 3 | `check_install_path` | executed | `install_path_resolved=false` — "Maven Central: org.aspose:aspose-pdf-foss NOT FOUND (0 results)" |
| 4 | `stop_and_report` | converged | *"The repository has a complete README (8074 chars) with license, com link, and relationship explanation, but is missing the org link; additionally, it is not published on Maven Central under the expected coordinates."* |

Every capability was requested exactly once, in a sensible order (broad inspection first,
narrower checks after), with zero duplicate or unregistered `capability_id` requests across the
run. The final `stop_and_report` summary is a **correct, non-hallucinated synthesis** of all
three prior real tool results — round 2's real finding (missing `.org` link only) matches this
project's own existing pilot characterization of `pdf/java` in `plans/master.md` decision #10
("partial-gap proof — missing only `.org`"), independently reproduced here through the new loop
mechanism rather than the shipped deterministic pipeline. Full redacted trace:
`plans/investigations/evidence/agentic-loop-proof/loop-trace.json`.

Total wall-clock: 4 live planning calls, 2.3–3.6s latency each — consistent with L8's finding
that tool-calling carries no meaningful latency tax over plain chat.

## Dispatcher safety gates exercised (by design, not by accident)

`prove_agentic_loop.py`'s dispatch loop enforces, mirroring decision #26(c)'s "never trusted as
an effect by itself" principle at spike scale:

1. `capability_id not in CAPABILITIES` -> `rejected_unknown_capability`, execution refused.
2. Already-called capability requested again -> `rejected_duplicate_capability`, execution
   refused (a minimal, spike-scoped stand-in for `ORC-001`'s cycle rejection).
3. Malformed `arguments` JSON -> `invalid_arguments_json`, execution refused.

None of these paths fired in this run (the model never requested an invalid or duplicate
capability across either the 3-round or 4-round attempt below) — they exist as gates that were
exercised structurally (present and would fire) rather than as an adversarial test. Adversarial
gate-firing (a model requesting something it shouldn't) is Wave 1's negative-control territory
for a later, more deliberately hostile spike, not this proof.

## Deviation from plan

First run used `max_rounds=3` (matching the plan's "iteration cap (3) as a spike safety net").
The model correctly used all 3 rounds on the 3 real capabilities and had no round left to call
`stop_and_report` — a parameter-tuning miss, not a loop-design defect (evidence:
`round_record` for round 3 still shows `outcome=executed`, not a forced/truncated failure). Bumped
to `max_rounds=4` and reran for the clean convergence trace above; the `3`-round run's raw
evidence was overwritten by the `4`-round run (same output path, matching this project's existing
probe-script convention of one evidence file per script, not one per invocation).

## Design consequences for later waves

1. **Wave 2's `CapabilityManifest`** can encode `required_inputs`/`produced_outputs` directly as
   the JSON-schema `parameters` block already proven reliable here (L6) — no separate schema
   language needed for tool declaration.
2. **Wave 5's supervisor** should keep the "one capability per planning turn" discipline (L7) as
   the portable baseline across routed models, not assume parallel tool calls.
3. **The dispatcher-side gates** (unknown/duplicate/malformed-arguments rejection) proven here at
   spike scale are the minimum bar `ORC-001`'s real cycle-rejection and permission checks must
   clear — this spike is evidence they are practically enforceable at the same layer that talks to
   the model, not just a design aspiration.
