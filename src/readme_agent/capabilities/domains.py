"""Registered agent-domain identifiers (`CAP-006`, Decision #33) -- the
caller-identity axis, orthogonal to `schema.py`'s `PermissionClass` blast-
radius axis. A registered set, not a closed `Literal`: the specialist list
(Wave 7) is expected to grow wave-by-wave, and a `Literal` would force a diff
to this lowest-level module every time, exactly the if/elif-chain-style churn
`AGENTS.md`'s "no monoliths" convention forbids elsewhere.

`README_RECONCILIATION` is the first real domain (Wave 6, decision #39) --
`registry.py`'s build-time checks were genuine no-ops until this entry
existed; adding exactly one domain does not itself trip the fail-closed
sunset (that needs `len(KNOWN_DOMAINS) > 1`), so no existing capability
becomes newly restricted by this addition.

`GITHUB_GENERATED_SURFACE_AUDIT` (Wave 7b) is the second -- once it lands,
`len(KNOWN_DOMAINS) > 1` becomes true for the first time, live-proving
`CAP-006`'s cross-domain-denial path and `MEM-004`'s multi-domain-collision
path, both previously only unit-tested.

`PACKAGE_RELEASE_AUDIT` (Wave 7c) is the third -- class D per `docs/
github-surface-control.md` (releases, packages): product-agent owned,
audit/handoff only, no write path here either.

`METADATA_PRESENTATION` (Wave 7d) is the fourth -- class B (description,
homepage, topics): dry-run proposal only this wave, per `OWN-006` -- no
GitHub API PATCH is ever attempted; the real apply gate is a later phase.

`COMMUNITY_FILES_PRESENTATION` (Wave 7e) is the fifth -- class 1 per `docs/
github-surface-control.md` (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT,
SECURITY, SUPPORT, templates): a real eventual write path exists for this
class (unlike classes 4/5), but this wave stops at audit + prepared
candidate content -- no write into any work clone yet, deliberately: 7g
registers this project's first real `local_write` capability, and nothing
here registers a second one in the same wave.

`CROSS_SURFACE_VALIDATION` (Wave 7f) is the sixth -- not tied to any single
GitHub-surface-control class, since it reads sibling domains' already-
recorded `DomainStateV1` entries directly (`state/backend.py::load()`)
rather than dispatching any capability of its own. Mitigates two specialists
independently forming an opinion about the same underlying fact (today:
`readme_reconciliation`'s README-text license claim vs. `community_files_
presentation`'s independently-detected LICENSE file classification) --
requires `specialists/registry.py::SpecialistManifest.depends_on` to
guarantee its dependencies' `record` nodes have already run in the same
pass, since nothing else orders specialist dispatch.

`README_PRESENTATION` (Wave 7g) is the seventh -- deliberately separate from
`README_RECONCILIATION` (a different domain, not a rename): this is the one
real mutating capability this project registers, `commit_readme_write`,
gated end to end by the permission-class check (`local_write`), the
domain-isolation check (`allowed_domains=[README_PRESENTATION]`), and
`entry.mode == "full"` (checked inside the capability itself, not inherited
from `supervisor/loop.py::_dispatch_and_record()`'s own mode gate -- that
gate only ever runs for the general planner's dispatch path, which this
domain-scoped capability can never reach in the first place). Closes
`EFF-001` on live proof.

`VISUAL_PREPARATION` (Wave 7h) is the eighth -- prepare-only, no capability
of its own registers a write path this wave. Audits for an existing image
asset (dimensions/format/size, via Pillow, per `GOV-015`) and, when none
exists (the common case across this project's own registry -- confirmed by
a real GitHub code search, zero image assets across the sampled pilots),
prepares a real, freshly-generated candidate banner from the pilot's own
product facts rather than fabricating or sourcing one -- deliberately
deferred from ever writing/embedding it into `README.md`: `readme/
markers.py`'s own docstring records a real, confirmed prior failure of
exactly this pattern (the retired `callout` span, a second owned region
alongside `resources`, pulled for a real link-duplication bug), and 7g's
write mechanism has had exactly one live proof so far -- not yet the real
mileage a second owned region would need before this project invents one.

`INDEPENDENT_VERIFICATION` (Wave 8b/8c) is the ninth -- the real `VER-001`
independent verifier, CAP-006-scoped (decision #34) exactly like every prior
domain. Two facets under one domain identity (decision: build both, not
either, per the Wave 8 design): (8b) an in-graph pre-apply gate --
`verify_readme_candidate`, dispatched by `specialists/readme_presentation.
py`'s own new `_verify_node` under `caller_domain=INDEPENDENT_VERIFICATION`
-- is the literal, strongest reading of VER-001's "sole authority accepting
it before it becomes... applied" for the one real write this project has
(`commit_readme_write`); (8c) a post-hoc cross-domain auditor (`specialists/
independent_verification.py`'s own `run()`), structurally identical in shape
to `cross_surface_validation` (`depends_on` every other domain, reads
sibling `DomainStateV1` state directly, no capability dispatch of its own
for that facet), housing the "adversarial checks / requirement mapping /
evidence completeness" duties Wave 8's own Build Checklist line names --
honestly post-hoc, not a blocking guarantee: it can only surface a finding
for the next run, never block the run whose effects already applied.
`specialists/readme_presentation.py` is the one deliberate exception to
"one module, one domain identity" in this codebase -- it dispatches under
`README_PRESENTATION` for its own render/commit nodes and under
`INDEPENDENT_VERIFICATION` for its verify node, made a real boundary (not a
convention) by `commit_readme_write`'s required `verification_verdict`
argument: the dispatcher's own pre-existing required-argument check means
that capability cannot be dispatched at all without it, so a future wiring
bug that skips the verify node fails closed (a missing-argument
`execution_error`), never silently bypassed.

`PRESENTATION_BENCHMARKING` (Wave 8.6) is the tenth -- a genuinely new
specialist *responsibility* (ongoing comparison of the current presentation
against the codified `docs/presentation-standard.md`), not a facet of any
existing domain: `INDEPENDENT_VERIFICATION` is reserved for `VER-001`'s
author/verifier split, not general benchmarking. Closes a gap found in an
external-review reconciliation session: this project's own one-time human
research (`plans/investigations/reference-repository-benchmark.md`) fed a
static standard document, but nothing made comparison against it an ongoing
runtime check until this domain existed.
"""

README_RECONCILIATION = "readme_reconciliation"
GITHUB_GENERATED_SURFACE_AUDIT = "github_generated_surface_audit"
PACKAGE_RELEASE_AUDIT = "package_release_audit"
METADATA_PRESENTATION = "metadata_presentation"
COMMUNITY_FILES_PRESENTATION = "community_files_presentation"
CROSS_SURFACE_VALIDATION = "cross_surface_validation"
README_PRESENTATION = "readme_presentation"
VISUAL_PREPARATION = "visual_preparation"
INDEPENDENT_VERIFICATION = "independent_verification"
PRESENTATION_BENCHMARKING = "presentation_benchmarking"

KNOWN_DOMAINS: frozenset[str] = frozenset(
    {
        README_RECONCILIATION,
        GITHUB_GENERATED_SURFACE_AUDIT,
        PACKAGE_RELEASE_AUDIT,
        METADATA_PRESENTATION,
        COMMUNITY_FILES_PRESENTATION,
        CROSS_SURFACE_VALIDATION,
        README_PRESENTATION,
        VISUAL_PREPARATION,
        INDEPENDENT_VERIFICATION,
        PRESENTATION_BENCHMARKING,
    }
)
