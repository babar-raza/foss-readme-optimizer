# G4 — L8-PF-02 canary outcome (Aspose.3D-FOSS-for-Python, live)

Claimed `L8-PF-02-COMPLETE-CANDIDATE-SEAM` through the governed path
(`--mission-action claim`, observer `readme-agent-supervisor`, state_version 1793) and ran the
canonical runtime:

```
supervise --repo aspose-3d-foss/Aspose.3D-FOSS-for-Python --execution-profile local_poc
         --bounded-verified-canary --mission-task-id L8-PF-02-COMPLETE-CANDIDATE-SEAM
         --mission-observer readme-agent-supervisor
```

## Result

```
BLOCKED (specialist_failed:readme_presentation:ERROR:independent_review_repair_rerouted:REJECT_REPAIRABLE;
         category=agent_fixable) [llm_accounting=EXACT; provider_calls=57; cache_reuse=4]
EXIT=1
```

Source revision `d9f3bfe50d47e8156266955dda52ec5abf2d9dec`; candidate hash
`59565a29deb739fbd240b38453bcfb4528d3138c44abf21034760f971203751c`.

## What advanced

- Stage receipts reached `CANDIDATE_GENERATED` and `DETERMINISTIC_VALIDATED`.
- `final-verdict.json`: `deterministic_validation_passed: true`, `repair_attempts: 1`.
- The **factual** reviewer returned `factual_plan:ACCEPT`.
- 48 bounded review packets were written under `review/bounded-packet-cache/` — the exact
  directory whose enumeration this sprint repaired. The run did **not** fail on
  `artifact_inventory_invalid`, which is what previously made this bundle unreusable.

## Where it stopped, exactly

The **blind visitor-quality** reviewer returned `REJECT_REPAIRABLE` on four findings in two
sections, and the single bounded repair attempt was rerouted rather than accepted:

| Section | Criterion | Span the reviewer objected to |
|---|---|---|
| additional-examples | example_presentation | "The examples below demonstrate loading OBJ files with materials, exporting a scene to binary GLTF, converting a parametric primitive to a mesh, and building a cube and exporting it to 3MF." |
| additional-examples | clarity | same span |
| scope-and-limitations | clarity | "The library targets the workflows listed above. Five specific constraints are listed below." |
| scope-and-limitations | promotional_balance | the Enterprise Edition paragraph |

`failed_criteria: ["clarity", "example_presentation", "promotional_balance"]`.

## Why this matters for the mission, stated precisely

The first failing boundary for `L8-PF-02` has moved from an infrastructure defect to a content
judgment. That is progress, and it is also the exact structural pattern this sprint set out to
characterise: the pipeline composes a candidate, a deterministic gate accepts it, an LLM reviewer
rejects it on prose quality, **one** bounded repair runs, and the run then stops and escalates.
There is no deeper self-repair loop, so a human or coding agent is the only remaining remediation
path for this class.

This is a legitimate, evidence-backed `BLOCKED` disposition with `category=agent_fixable` — not a
crash, and not an external blocker. The named spans and criteria are a directly actionable repair
brief for the next execution cycle.

## Honest limits of this run

- It is a **bounded verified canary**: partial repository proof only. It does not satisfy
  full-registry Gate A, and the runtime says so in its own first output line.
- `NO_OP_PROVEN` was not reached, so this run does not prove the inventory repair end-to-end
  through a no-op replay. It proves only that the run no longer stops at
  `artifact_inventory_invalid` and that the packet cache is written and enumerable.
- One repository is not the portfolio. 33 others remain, most with their own distinct
  blocked-decision records.
