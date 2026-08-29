# Cycle 2 — why L8-PF-02's repair loop cannot close, root-caused

> **SUPERSEDED IN PART — read `c2-correction-pf02-root-cause.md` first.**
> An independent verification lane refuted the central claim of this artifact and I confirmed its
> evidence directly. What follows is a real defect and remains worth fixing, but it is **not** the
> proximate cause of PF-02's `candidate_changed: False`. The proximate cause is that
> `scope-and-limitations` *did* route, the author *was* called, and deterministic acceptance
> discarded every unit it produced. Fixing the slot gap alone would not have unblocked PF-02.

The `aspose-3d-foss/Aspose.3D-FOSS-for-Python` canary reran at source revision `d9f3bfe50d47`
(`provider_calls=2, cache_reuse=58`, `llm_accounting=EXACT`) and rerouted again at
`independent_review_repair_rerouted:REJECT_REPAIRABLE`. That much was already known. This artifact
records *why*, which was not.

## What the repair receipt actually says

`review/repair-history.json`, attempt 0:

```
candidate_changed        : False
changed_operation_ids    : []
rereview_authorized      : False
addressed_finding_ids    : []
unresolved_finding_ids   : [4 findings, all unresolved_unchanged]
```

Every finding: `section_changed: False`, `prior: 1 repaired: 1`,
`bound: ['readme.verified-template.compile']`, `changed_bound: []`.

The four findings (from `review/blind-quality-review.json`):

| finding | criterion | section |
|---|---|---|
| `pkt.visitor.0007.additional.examples.7e2ff7845c70.f1` | `example_presentation` | additional-examples |
| `pkt.visitor.0007.additional.examples.7e2ff7845c70.f2` | `clarity` | additional-examples |
| `pkt.visitor.0011.scope.and.limitations.40b1bd1faf14.f1` | `clarity` | scope-and-limitations |
| `pkt.visitor.0011.scope.and.limitations.40b1bd1faf14.f2` | `promotional_balance` | scope-and-limitations |

## Root cause 1 — the reviewer's scope is wider than the repair layer's

`review/bounded-review-plan.json` for this candidate contains **14 visitor packets across 13 section
roots**:

```
additional-examples, api-reference, at-a-glance, dependencies, development-and-testing,
documentation-resources, front-matter, installation, key-capabilities, license, navigation,
quick-start, scope-and-limitations
```

`readme/section_authoring_specs.py::_SECTION_FIELDS` defines **5** authoring slots: `summary`,
`key_capabilities`, `installation`, `quick_start`, `scope_and_limitations`.
`specialists/section_authoring_repair.py::_REVIEW_SECTION_TO_AUTHORING_SLOT` maps six section names
onto those five.

So **8 of the 13 reviewable roots have no section-authoring repair route at all**:
`additional-examples`, `api-reference`, `at-a-glance`, `dependencies`,
`development-and-testing`, `documentation-resources`, `license`, `navigation`.

For a finding in one of those, `_slot()` returns `None` and the finding never enters `by_slot` —
it is dropped with no record. And because

```python
rereview_authorized = bool(findings) and not unresolved_ids
```

(`readme_repair_validation.py`), **one unroutable finding is enough to disable the entire repair
loop for that repository**, no matter how repairable the others are. Two of PF-02's four findings
are in `additional-examples`. The loop never had a path to success.

The reroute reason names none of this. It reports a generic "did not materially change every
responsible span/operation", which is why this presented for two cycles as a mysterious
byte-identical repair.

**Caveat recorded deliberately:** `at-a-glance` *is* repairable, but through the composition
re-planning path (`plan_readme_composition` with `review_repair=`), not through section authoring.
So the two repair mechanisms must be considered together before declaring any root unowned — the
count of 8 is an upper bound on "no section-authoring route", not a proven count of "no route at
all".

## Root cause 2 — a producer/reviewer contract conflict

The first `additional-examples` finding reads:

> First paragraph is a raw task list, not a natural workflow preview.

quoting:

> The examples below demonstrate loading OBJ files with materials, exporting a scene to binary
> GLTF, converting a parametric primitive to a mesh, and building a cube and exporting it to 3MF.

That sentence is **deterministically generated** by
`presentation/verified_template_example_presentation.py`, and `presentation/template_schema.py`
pins `additional_examples_intro: Literal["workflow_preview"]`. The reviewer's
`example_presentation` and `clarity` criteria reject exactly the shape that generator is specified
to emit.

No prompt change and no repair loop can resolve that; only changing the generator can. And that
changes every repository's additional-examples section, so it needs the dual-hash shadow period the
plan already requires for fleet-wide presentation changes — not a point fix.

## Corroboration from a second repository

`aspose-3d-foss/Aspose.3D-FOSS-for-.NET` is blocked at
`independent_review_exception:RuntimeError: bounded aggregate grounding failed` on two
`pkt.visitor.0008.api.reference...` findings. `api-reference` is also one of the 8 roots with no
authoring slot. Same family, failing one stage earlier.

## Disposition

`ACL-REVIEW-REPAIR-SCOPE-MISMATCH` (P0, blocker). The forbidden fix is explicitly recorded on the
card: making `rereview_authorized` ignore unaddressed findings would "resolve" this by accepting
prose the reviewer rejected, which is lowering the bar, not clearing it.

`L8-PF-02-COMPLETE-CANDIDATE-SEAM` was transitioned to `BLOCKED` (agent_fixable) with this root
cause and an exact resume condition recorded on the transition, rather than left holding an
expiring claim.
