# Cycle 2 — the portfolio blocker leverage map, measured

Read from all 31 `runs/readme-poc/*/blocked-decision.json` records at HEAD `37b7a7517`.
104 cumulative live reproductions across them. This replaces asserted prioritisation with counted
prioritisation; the plan previously ranked work by argument.

## By cause

| Blocked cause | Repos |
|---|---|
| **claim accountability** | **10** |
| `product_truth_not_ready:BLOCKED_MISSING_EVIDENCE` | 6 |
| `LLMTruncatedResponseError` (composition) | 3 |
| `LLMInfrastructureError` (forced tool call failed after retries) | 3 |
| `composition.segmen…` | 2 |
| bounded aggregate grounding failed | 1 |
| `local_poc_candidate_persistence:ValueError` | 1 |
| compiled verified presentation invalid | 1 |
| `check_unqualified…` / `template.section.a…` / `verified_omissions…` / `presentation.forma…` / `unauthorized prote…` | 1 each |

## By lifecycle status

| Status | Repos |
|---|---|
| `FACTS_READY` | 20 |
| `BLOCKED_MISSING_EVIDENCE` | 8 |
| `SYSTEM_FAILURE` | 1 |
| `README_ASSESSED` | 1 |
| `DETERMINISTIC_VALIDATION_FAILED` | 1 |

## The largest lever, and why it is not a gate to loosen

All 10 claim-accountability blockers sit at `FACTS_READY`, and **6 of the 10 have exactly one
blocking claim**:

```
Aspose.3D-FOSS-for-TypeScript   blocking=8   consec=4
Aspose.Cells-FOSS-for-Java      blocking=1   consec=1
Aspose.Cells-FOSS-for-Rust      blocking=11  consec=1
Aspose.Email-FOSS-for-Python    blocking=1   consec=7
Aspose.Page-FOSS-for-Python     blocking=1   consec=6
Aspose.PDF-FOSS-for-.NET        blocking=12  consec=2
Aspose.PDF-FOSS-for-Java        blocking=1   consec=1
Aspose.Slides-FOSS-for-Java     blocking=1   consec=2
Aspose.Slides-FOSS-for-Python   blocking=1   consec=9
Aspose.Words-FOSS-for-.NET      blocking=4   consec=5
```

`claim_accountability_validation.py`:

```python
blocking = sorted(record.claim_id for record in accountability.claims
                  if not record.currently_accountable)
```

A blocking claim is a claim the **source** README makes that the candidate neither preserves nor
records a resolution for. That is the preservation property the entire product rests on — the
reason this system is trustworthy at all. The lever is to resolve or record those claims, never to
stop counting them. Six repositories needing one claim each is the cheapest real portfolio progress
available, and it is content work, not a code fix.

## Second-largest, and a different kind of problem

Six repositories are `product_truth_not_ready:BLOCKED_MISSING_EVIDENCE` — they cannot establish
product truth at all, so no amount of composition or review work reaches them. Distinct root cause,
distinct fix.

## Infrastructure-only failures: 6 of 31

Three `LLMTruncatedResponseError` (fixed this cycle — see the truncation artifact) and three
`LLMInfrastructureError: forced tool call failed after retries`. These have nothing to do with
content quality; they are provider-reliability and prompt-budget failures. Roughly a fifth of the
blocked portfolio is failing for reasons unrelated to whether the agent can write a good README.

## Honest reading

The mission is every processable repository at 30/30 with an immediate complete-transaction no-op.
Contract-valid counters read `facts_ready 1/34`, `no_op_proven 0/34`. This map does not shorten that
distance — it makes the distance legible, and it says which of several plausible next moves is
actually the largest.
