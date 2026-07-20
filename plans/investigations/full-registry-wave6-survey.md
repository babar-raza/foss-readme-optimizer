# Full-Registry Wave 6 Survey — decisions #38/#39 hardening

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: `tools/survey_full_registry_wave6_reconciliation.py` — clones the baseline of all 25
> real `data/products.json` entries (every mode, per decision 24/`PIL-011`'s research-scope
> carve-out; read-only `clone_baseline()` throughout, never a work clone, never a push) and runs
> `file_inventory.scan()`, `compute_tracked_content_hash()`, `readme.reconciliation.classify()`,
> and `profile.detector.build_profile()` against each, real repo, real filesystem.

## Why this exists

The user asked for Wave 6's new code to be tested against every repo in the registry, its
results verified, and the process tweaked where needed — the same discipline Wave 3 applied to
the ecosystem parsers (`full-registry-ecosystem-detection-survey.md`, which found and fixed 2
real bugs). Wave 6's own live proof (2026-07-19) exercised exactly one real repo
(`aspose-cells-foss/Aspose.Cells-FOSS-for-Java`) plus a quick coarse-tier rerun — real, but not
broad. This closes that gap for the pieces that generalize across the whole registry:
`compute_tracked_content_hash()` (decision #38's fix) and `readme.reconciliation.classify()`
(decision #39's classifier) had, until this survey, only ever seen 2–3 real READMEs total.

**Scope boundary, stated up front**: only the 3 enabled entries carry a `policy_profile`, so
`get_product_facts`'s policy-dependent half (declared license, link specs, talking points) cannot
be exercised against the other 22 — there is no policy YAML to load for them. What *is* shared
and real for all 25 regardless of mode: file inventory (README/LICENSE/community-file detection),
the content fingerprint, the drift classifier, and ecosystem profiling. This survey covers exactly
that, not a substitute for a full `get_product_facts` proof on every repo.

## Result: 25/25 clean, zero bugs found

```
25/25 repos surveyed without a crash
```

Every repo: a valid README found, a 64-character SHA-256 `tracked_content_fingerprint` computed
with no crash, a `readme.reconciliation.classify()` call returning `FIRST_OBSERVATION` (correct —
this survey never touches durable state, so every call is a first observation by construction) and
`owned_span_present_now=False` (correct — no repo in this registry has ever had this tool's
`resources` marker written to its real, upstream README; nothing is pushed there). Ecosystem
detection matched every declared platform 1:1 (`java`→`java`, `net`→`net`, `python`→`python`,
`typescript`→`typescript`, `go`→`go`, `cpp`→`cpp`), zero unresolved manifests — Wave 3's own fix
holds. Community files correctly detected in exactly the 3 repos that have them:
`aspose-email-foss/Aspose.Email-FOSS-for-Python` (`CONTRIBUTING`, `SECURITY`),
`aspose-font-foss/Aspose.Font-FOSS-for-Python` (`SECURITY`), `aspose-pdf-foss/aspose-pdf-foss-for-go`
(`CONTRIBUTING`).

One repo, `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`, reported `has_license_file=False`.
Verified directly (not assumed): its real, cloned root contains no `LICENSE`/`LICENSE.txt`/
`LICENSE.md`/`COPYING`/`LICENSE.rst`, in any casing, and no `license/` subdirectory —  a genuine
gap in that specific real repo's own root, not a detection miss. Decision #5 already treats a
missing/undetected license as a soft-degrade, never a hard block — this is that case working
correctly, not a new finding.

Full raw results: `plans/investigations/evidence/full-registry-wave6-survey/survey-results.json`.

## Regression proof: the 3 real enabled pilots, live, with real durable state

Beyond the read-only survey above, all 3 enabled pilots were run through the real, production
`supervise --durable-state` path (real gateway planner, real remote — this project's own
`refs/readme-agent-state/...` ref only, never a target repo) this session and the prior one:

| Pilot | Real gateway planner run | Specialist domain state recorded |
|---|---|---|
| `aspose-cells-foss/Aspose.Cells-FOSS-for-Java` | 2026-07-19 — dispatched `inspect_repository` → `detect_readme_gaps` → `get_product_facts`, converged | `readme_reconciliation` → `FIRST_OBSERVATION` |
| `aspose-pdf-foss/Aspose.PDF-FOSS-for-Java` | 2026-07-19 — converged via the coarse tier (real prior state from Wave 5) | already recorded from Wave 5 |
| `aspose-3d-foss/Aspose.3D-FOSS-for-Java` | 2026-07-20 — dispatched `inspect_repository` → `profile_repository` → `get_product_facts` → `detect_readme_gaps` → `check_install_path`, converged | `readme_reconciliation` → `FIRST_OBSERVATION` |

`aspose-3d-foss/Aspose.3D-FOSS-for-Java`'s run is the most complete single proof produced so far:
the real planner chose and successfully dispatched **five of six** registered capabilities in one
run (every one except `classify_upstream_change`, which the `readme_reconciliation` specialist
itself already dispatches deterministically, before the planner loop starts — so it ran too, just
not as a planner-visible choice). Confirmed by reading the durable record back: both
`domain_states["readme_reconciliation"]` and `supervisor_state` present in the same record, on the
real remote, for a third real repo — decision #38's multi-producer coexistence fix now proven
against all 3 enabled pilots, not just one.

## What was tweaked

Nothing. This is the honest result, not a rounding-down: no crash, no misclassification, no
detection regression across 25 real, diverse repos plus 3 full live `supervise` runs. The one
process refinement made *while preparing* this survey (not a finding *from* running it) was
recognizing the `OPS-009` git-push-credential hang within minutes on the `aspose-3d-foss` live run
— a rehearsed response now, not a fresh diagnosis, and removed immediately after per the
documented discipline.

## Honest limits, not glossed over

1. **`get_product_facts`'s policy-dependent output is still only proven for 3 repos.** Freezing
   the full decision #22 product-facts schema and populating `policy_profile`/`config/policies/*.yml`
   for the other 22 remains `DOC-006`, still `RESEARCH-GATED` — unchanged by this survey.
2. **`readme.reconciliation.classify()`'s non-`FIRST_OBSERVATION` branches (`NO_CHANGE`,
   `UPSTREAM_CHANGED`, `OWNED_SPAN_LOST`, `MIXED_CHANGE`) are still only proven live for one repo**
   (`aspose-cells-foss/...-Java`, via two back-to-back `supervise` calls) plus unit tests with
   synthetic text. This survey exercised only the `FIRST_OBSERVATION` branch at scale, by
   construction (no durable state ever supplied) — a real, stated limit, not silently smoothed over.
3. **`aspose-page-foss/Aspose.Page-FOSS-for-Python`'s profiling latency (~258s this run, ~176–186s
   in Wave 3's) is unchanged** — the already-documented, already-accepted-as-open large-repo
   `os.walk` cost (Wave 3's own "what did not improve" item), not reopened or worsened here.
4. **The specialist/LangGraph layer's domain-*denial* path and genuine multi-domain collision
   remain unit-only** (`CAP-006`/`MEM-004`, `plans/requirements.md`) — this survey and the 3 live
   `supervise` runs all exercised the *allowed* path of a single domain, never a second domain or a
   rejected cross-domain call. Still gated on Wave 7's second specialist, as already stated.

## Summary

Wave 6's new, previously narrowly-tested code (`compute_tracked_content_hash`,
`readme.reconciliation.classify`) holds up cleanly across the real registry's actual diversity —
6 platforms, repo sizes from a few files to ~2500, README lengths from short to long, presence and
absence of LICENSE/community files. All 3 enabled pilots now have a real, live `supervise`
run recorded, not just one. No code change was needed as a result of this survey; the survey
itself, and this document, are the delivered evidence.
