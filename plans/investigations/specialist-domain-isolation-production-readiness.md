# Specialist Domain-Isolation Production Readiness — root-cause assessment ahead of Wave 6-8

> governed_by: `plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)`
> artifact_role: analysis_or_evidence_only · execution_authority: false
> method: direct source inspection of `src/readme_agent/capabilities/` (`schema.py`, `registry.py`,
> `dispatcher.py`), `src/readme_agent/state/` (`schema.py`, `backend.py`, `git_backend.py`), and
> `src/readme_agent/readme/markers.py`; full re-read of `plans/master.md` decisions #26/#27/#32,
> `plans/investigations/runtime-framework-evaluation.md`,
> `plans/investigations/capability-dispatch-production-readiness.md`, and
> `plans/investigations/agentic-loop-proof.md`; two independent desk-research passes on real,
> current, third-party alternatives (authorization/access-control libraries; durable multi-writer
> state-coordination primitives), each verified against primary sources (PyPI/GitHub release dates,
> vendor documentation, git's own wire-protocol documentation) rather than asserted from memory.

## Why this exists

Waves 6-8 of the sprint reset (`plans/master.md` Build Checklist) will replace the single
not-yet-built Wave 5 planner with roughly seven independent "specialist" sub-agents (README,
metadata, community files, visuals, package/release auditor, GitHub-surface auditor, cross-surface
validator) plus Wave 8's independent verifier — each meant to be confined to its own domain. This
document root-causes what "confined to its own domain" actually requires, ahead of that work
landing, and asks the production question directly for each sub-problem it decomposes into: **would
a hand-rolled extension of what's already built hold up in repeated real use, or does a real,
currently-maintained, proven tool exist that would do better — and is any apparent gap a symptom of
something deeper than a local patch fixes?**

This is the third pass on this question. The first treated it as one question ("which framework?")
and stopped at a documentation-only addendum. The second root-caused four gaps but designed
hand-rolled fixes for two of them without ever testing that choice against real alternatives —
inconsistent with having separately adopted a proven framework (LangGraph) for specialist/subgraph
composition. This document supplies the missing evidence for the two "extend vs. adopt" sub-problems
that framework choice does not resolve.

**Framing that shapes every finding below**: `src/readme_agent/capabilities/` has zero production
callers today (confirmed by the prior `capability-dispatch-production-readiness.md` audit, unchanged
since). All four registered capabilities are read-only; `domains.KNOWN_DOMAINS` is empty. Everything
below is preemptive hardening ahead of Wave 6, not incident response — every claim is scoped to that
honestly, and confidence levels are stated per finding rather than implied uniformly.

## Symptoms, root causes, structural weaknesses

### Symptoms

- Decision #27 left "subgraph/specialist-role composition" (Wave 7+) as an open, unresolved revisit
  trigger.
- `capabilities/dispatcher.py` (pre-this-pass) checked only a capability's self-declared
  `side_effect_class`; `required_permissions` was declared per manifest but never read by anything.
- No requirement row anywhere used the word "domain"; `ORC-003` requires specialists be
  auto-invoked, not that they be isolated from each other.
- `state/schema.py`'s `RunStateV1` (pre-this-pass) had exactly one `accepted_facts_hash`/
  `accepted_status` pair per `org_repo`, on one `state_version` CAS counter, for the whole record.
- `EFF-001/002/003` (effect idempotency) are `PLANNED`, traced generically to "Wave 5," with no
  stated dependency on Wave 7 even though Wave 7 is what will actually register the first
  `local_write`/`remote_write` capability.
- The only live evidence for LLM planning reliability is N=1 (one successful run, one model, one
  planner) — already flagged as insufficient by `capability-dispatch-production-readiness.md`.

### Root causes

1. **The schema has one axis (blast radius, `side_effect_class`) where a second, orthogonal axis
   (caller identity/domain) is needed and has never existed**, because until Wave 6 there was only
   ever one caller to authorize. Confirmed directly against `dispatcher.py`'s pre-this-pass source:
   it did exactly what its schema modeled — a missing schema dimension, not a bug in the function
   that reads it.
2. **`RunStateV1` was designed to answer "did *the* run for this repo produce an accepted result,"
   singular, because there was one producer.** Confirmed directly against
   `git_backend.py::save()`'s actual mechanics: it is a whole-blob replace under one tree path
   (`"state.json"`, one `mktree` entry). Two specialists writing into the same per-repo record would
   either false-positive collide on the CAS check or silently clobber each other's already-accepted
   result — the same bug class Decision #32 already found and fixed once (CAS granularity coarser
   than the real concurrency unit), reappearing one layer further down (per-repo record → per-domain
   sub-record).
3. **Effect-safety (`EFF-*`) was scoped to "Wave 5" as a generic future concern, when the actual
   forcing function is Wave 7** (first wave that plausibly registers a mutating capability). The
   dependency is real but was never stated as a registration-time gate.
4. **"Domain independence" is being used to mean at least three different things, only one of which
   any existing mechanism addresses**: (a) which capabilities a specialist's LLM may call; (b) which
   repo files/surfaces a specialist may write to, independent of which capability does the writing
   — `markers.py`'s job today, scoped to one owner (`SPAN_NAMES = ("resources",)`); (c) which
   durable state a specialist's result occupies without colliding with another's — root cause #2.

### Structural weakness underneath all four

This project has a proven, successful pattern — "reserve a field now with inert semantics, give it
real meaning in the wave that needs it" (`idempotency_inputs`, `retry_policy`, `cache_policy`, all
shipped this way in Wave 2, per `schema.py`'s own stated field-population policy). That pattern is
safe for reliability/performance fields. It was applied, by default, to what turns out to be an
**access-control** field (caller domain) and a **concurrency-control** field (per-domain state) — a
reserved-but-unenforced access-control field is a materially different risk than a
reserved-but-unenforced performance field, and nobody had flagged that distinction before this pass.

## What is actually breaking consistency across reruns

1. **False-positive staleness or silent clobbering** between two specialists writing the same
   `org_repo` state record in one run (root cause #2).
2. **Duplicate remote effects on a real, public repository** — the realistic trigger is GitHub
   Actions' ordinary "re-run failed jobs" button: a `remote_write` capability succeeds, an unrelated
   later step fails, a human re-runs the job, the same capability fires again with no idempotency
   check. A quieter variant: a partial effect gets fingerprint-cached as "done" before its
   correctness is confirmed, and the next run's cache hit silently accepts a broken result as final.
   Both are foreclosed by `EFF-001`'s own already-specified registration-time gate.
3. **Unmeasured, structurally-real reliability compounding** across ~7 independent specialist
   planning calls per run, with only N=1 evidence for a single planner today. No numeric claim is
   possible from current evidence (confidence: none — deliberately, not estimated). The durable
   mitigation is per-specialist failure isolation, extending `GAP-001`/`SCL-001`'s already-committed
   "isolate the failure, don't invalidate unrelated already-accepted work" principle one level down
   — representable in durable state only once root cause #2 is fixed.

## Sub-problem 1: domain/permission enforcement — hand-roll vs. adopt

**Candidates researched, with verified maintenance status:**

| Candidate | Status (verified, with source) | Why rejected |
|---|---|---|
| Oso / Polar | **Deprecated Dec 2023**; last release v0.27.3, Jan 13 2024 — no release in ~2.5 years. Source: [osohq.com deprecation notice](https://www.osohq.com/docs/oss/any/getting-started/deprecation.html) | Abandoned. Adopting it would import exactly the troubleshooting risk `GOVERNANCE.md` rule 8 exists to avoid. |
| py-abac | Last release v0.4.1, Nov 18 2020. Source: [pypi.org/project/py-abac](https://pypi.org/project/py-abac/) | Abandoned (5+ years stale); also requires an external MongoDB/SQL backend. |
| Vakt | No PyPI release in 12+ months, low download volume. | Abandoned; py-abac's own predecessor. |
| OPA (Open Policy Agent) | Core project healthy, but **no official embedded-Python evaluator** — the supported Python path is a REST call against a sidecar/daemon process (`opa-python-client`); the WASM-embed alternative relies on niche, single-maintainer, unofficial bridge libraries. Source: [openpolicyagent.org/docs/integration](https://www.openpolicyagent.org/docs/integration) | Sidecar path reintroduces exactly the "new infrastructure/process" surface this project has already avoided elsewhere (mirrors why an external state DB was rejected in Decision #32). WASM path trades the sidecar for a build pipeline + unofficial bridge — arguably more fragile for a problem this small. |
| Cedar (`cedarpy`) | Actively released (latest v4.8.7, Jul 10 2026), Apache-2.0 — but explicitly third-party/unofficial, maintained by a small security consultancy, not AWS. Purpose-built for schema-validated, multi-tenant SaaS resource authorization. Source: [github.com/k9securityio/cedar-py](https://github.com/k9securityio/cedar-py) | Real and current, but a compiled native-code (Rust/PyO3) dependency from a single small maintainer, solving a materially different, larger problem than one dispatch-time list-membership check — the same disproportion shape as the PyGithub-vs-raw-`requests` rejection in Decision #28. |
| **Casbin (`pycasbin`)** | **Actively maintained**: latest v2.8.0 (Feb 2 2026), entered the **Apache Incubator** Feb 7 2026. Pure Python, two tiny pure-Python transitive deps (`simpleeval`, `wcmatch`). Ships a first-class "RBAC with domains" model — `(subject, domain, object, action)` — a near-literal fit. | **The one real, architecturally-viable candidate — still rejected.** Would duplicate the domain-permission data across two representations: the existing pydantic `CapabilityManifest` (already the single source of truth for every other capability contract field) vs. Casbin's own model/policy-file representation. Requires learning and maintaining a matcher DSL and an expression evaluator to re-derive a check that's already one line (`caller_domain not in manifest.allowed_domains`) against typed data already in hand. Mirrors Decision #27's own reasoning for rejecting a framework at the Wave-5 core-loop layer: importing a second, foreign representation for no compatibility gain. |

**Falsifiable revisit trigger** (Decision #33): if the domain model later needs hierarchy (a domain
inheriting another's capabilities), wildcard/pattern-based grants, or externally-supplied/
runtime-editable policy (not redeployed with code), **Casbin is the specific library to reconsider
first** — it is the only candidate that clears the architecture and maintenance bar; it simply
doesn't earn its cost against today's scope (a closed, project-registered set of ~7-10 domains, no
hierarchy, no runtime-editable policy requirement).

**Verdict**: extend the hand-rolled dispatcher/registry pattern. Implemented this pass:
`CapabilityManifest.allowed_domains: list[str]` (additive, empty = unscoped, unchanged meaning for
all four existing manifests); `capabilities/domains.py::KNOWN_DOMAINS` (a registered set, empty
today, genuinely inert); `registry.py::_build()` gains domain-membership validation plus a
fail-closed sunset (once `len(KNOWN_DOMAINS) > 1`, a mutating manifest with no `allowed_domains` is
rejected at build time — the engineered expiry of the "insecure by default" window,
`GOVERNANCE.md` rule 5); `dispatcher.py::dispatch_tool_call` gains a `caller_domain` parameter and
one new check.

**Why the dispatcher check, not a framework's tool-offer scoping, is the actual boundary**:
LangGraph's (or any framework's) per-node tool binding governs what a specialist's LLM can *request*.
It is ordinary orchestration-code wiring, not a sandboxed guarantee — a copy-paste bug in graph
construction, a stale tool list after a domain reassignment, or any hand-authored call straight into
`dispatch_tool_call` all silently bypass it, with no error anywhere. The dispatcher's
`allowed_domains`/`caller_domain` check is the one point every call path must cross regardless of
which graph node or bug produced it, because it's keyed off manifest data and a caller-supplied
identity, not off which schemas an LLM happened to be shown. This is not a claim that LangGraph
specifically is weak (its internals were not verified against source in this pass, flagged as an
assumption) — it's a claim that no orchestration-wiring-level mechanism is a hard guarantee, true
regardless of framework. Concretely, Wave 8's `VER-001` ("independent verifier... sole authority
accepting a proposal") depends entirely on this: if isolation were convention-only, a wiring bug
could silently hand the verifier the same mutating access as the capability it's supposed to be
checking, with nothing anywhere to catch it.

## Sub-problem 2: multi-writer durable state — hand-roll vs. adopt

**Evidence — git plumbing semantics, verified against primary sources (not asserted from memory):**

- `git mktree` genuinely supports multiple independently-addressable blob entries in one tree object
  (confirmed via [git-scm.com/docs/git-mktree](https://git-scm.com/docs/git-mktree)) — the current
  code's one-entry tree (`_write_commit`, `git_backend.py`) is the degenerate case, not a limit of
  the tool.
- **Non-fast-forward rejection is scoped to the ref as a whole, not to any path inside it**
  (confirmed via `git-receive-pack` behavior: the wire protocol's compare-and-swap is `old-value
  new-value ref-name` per ref, with no notion of "which paths changed"). This means a multi-blob tree
  layout does **not**, by itself, buy finer-than-ref-level conflict detection — two specialists
  writing to two different paths under the same ref can still race, and a retry step is unavoidable
  regardless of how the tree is shaped.

**GitHub-native alternatives researched:**

| Candidate | Verified behavior | Why rejected |
|---|---|---|
| GitHub Contents API | Same branch-HEAD-serialized-commit granularity as raw git, wrapped in HTTP. Corroborated by two independent community bug reports of cross-file SHA-mismatch 409s on concurrent PUTs to *different* files on the same branch ([community discussion #62198](https://github.com/orgs/community/discussions/62198), [PyGithub#1787](https://github.com/PyGithub/PyGithub/issues/1787)) — flagged explicitly as circumstantial corroboration, not an explicit GitHub statement of the mechanism. | No capability gain over what's already built; adds HTTP rate-limit exposure for nothing. |
| GitHub Issues/Discussions API | GitHub's own REST docs state plainly: conditional requests aren't supported for unsafe methods except where explicitly noted (Contents API's `sha` param is the one noted exception). | No real CAS available at all. |
| GitHub Actions cache | Confirmed immutable-once-written (existing key can't be overwritten, only deleted-then-recreated — itself race-prone), eviction-prone. | Wrong shape entirely — not durable storage. |
| GitHub Checks API | Scoped to a commit/check-suite context, no version/CAS field. | Not a coordination primitive at all. |

**External OCC stores — genuinely finer-grained, but reopen a question Decision #32 already closed:**

- **S3 conditional writes** (`If-None-Match`/`If-Match`, GA 2024) are a real, per-object-key
  optimistic-concurrency primitive — the one candidate researched that is technically superior in
  isolation to git's ref-level granularity for this exact problem.
- **DynamoDB conditional expressions** are the same story; GitHub Actions can authenticate to AWS
  credential-free via OIDC (a documented, standard trust-exchange flow, no long-lived secrets).
- **Both still reopen exactly what Decision #32 explicitly rejected**: a new AWS account
  relationship, a new bucket/table to provision and operate, a new IAM role/OIDC trust policy, a new
  dependency. Decision #32's own disproportionality reasoning ("per-repo state is a few KB") is
  unchanged by the multi-writer requirement — the record is still a few KB, just internally reshaped.
  None of #32's own named revisit triggers (state stops being a few KB, write volume outgrows what
  `git push` can absorb, a cross-repo query/dashboard need emerges) are met by this problem. A
  technically-better-fitting external option existing doesn't change whether adopting one is
  *proportionate*.

**SQLite-as-blob-content** (serialize the git blob's content as an SQLite file instead of JSON, for
local transactional guarantees before push) was examined directly and found to add nothing: git's
CAS operates at the ref level regardless of blob byte format — a stale push is rejected identically
whether the blob is JSON or SQLite. The only real effect would be losing `state.json`'s current
text-diffability in `git log -p`, a property this project already relies on elsewhere ("read the
actual state" is a first resort throughout the Decision Ledger).

**Verdict, stated precisely**: this is "proven primitive (git's ref-update CAS — the same mechanism
every git hosting provider relies on for push safety), right granularity (per-`org_repo`, unchanged
from Decision #32), payload shape needs to grow" — not a build-vs-adopt tool decision in the sense
first feared. A load→patch→save→retry-on-stale loop is the standard, expected complement to *any*
optimistic-concurrency primitive (git's, S3's, DynamoDB's alike); its presence doesn't indicate the
underlying primitive is inadequate.

Implemented this pass: `state/schema.py` gains `DomainStateV1` and `RunStateV1.domain_states: dict[str,
DomainStateV1]` (additive; the existing flat `accepted_facts_hash`/`accepted_status`/
`upstream_revision_at_accept` fields are not deprecated — they remain whatever a single top-level
producer writes). `state/domain_state.py::save_domain()` composes the *already-existing,
already-live-tested* `acquire_lock`/`release_lock` lease (`MEM-002`) as the primary serialization
mechanism, with the version-CAS retry as a correctness backstop for the lease-expiry edge case (a
lease is a timeout, not a hard mutex) — always re-patching onto a freshly reloaded copy so another
domain's already-accepted result is carried forward automatically, never overwritten. No change to
`GitStateBackend.save()`'s signature or whole-blob-replace mechanics was needed.

**Documented, not built**: an optional multi-blob tree layout (`domains/readme.json`,
`domains/metadata.json`, ... instead of one `state.json`) for per-domain audit clarity or reduced
per-write serialization cost. Still needs the identical retry loop (tree shape doesn't change
ref-level CAS granularity) — a nice-to-have layered on top, very likely unnecessary complexity at
Wave 7's actual scale (7 named specialists, one write each per run, record still "a few KB").

## Confidence summary

- **High, independently verified via primary/current sources**: all library maintenance-status
  claims (dates, releases); git ref-update CAS and `mktree` semantics; GitHub Issues/Discussions'
  lack of conditional-write support; GitHub Actions cache immutability; S3 conditional writes being
  real and per-object-key; GitHub Actions OIDC-to-AWS being credential-free.
- **High, verified directly against this repo's own source**: every claim about
  `dispatcher.py`/`registry.py`/`schema.py`/`git_backend.py`'s pre-this-pass behavior.
  Post-this-pass behavior additionally verified by a passing test suite (335 passed, 11 deselected
  live tests, zero existing tests modified for behavioral reasons).
- **Medium, explicitly flagged**: the Contents API "no finer-than-branch-level conflict detection"
  claim rests on two community bug reports, not an explicit GitHub statement — doesn't affect the
  recommendation (Contents API wasn't a candidate either way).
- **None, deliberately not estimated**: any numeric claim about LLM reliability at multi-specialist
  scale. The evidence to support one doesn't exist yet (only N=1, single-planner evidence).
- **Not verified in this repo**: LangGraph's actual internal tool-binding guarantees. The "framework
  ≠ enforcement boundary" argument doesn't depend on LangGraph specifically being weak — it depends
  on no orchestration-wiring-level mechanism being a hard guarantee, which holds regardless of
  framework — but this is stated as reasoning from general principle, not as a verified fact about
  LangGraph's specific implementation.

## What this does not do

Does not install or spike LangGraph — that adoption remains Wave 6-8 work; this document and its
accompanying code changes only build the enforcement/consistency layer that has to exist underneath
it regardless of which framework Wave 6 ultimately uses. Does not design the repo-surface/file
ownership generalization (`markers.py`'s single-span pattern extended to multiple specialists) —
logged against `OWN-011`, deliberately deferred because Wave 7's real specialist-to-surface mapping
doesn't exist yet and designing the mechanism before it does risks repeating Decision #32's own
first-draft mistake (a granularity guess made before the real concurrency shape was known). Does not
produce a live, multi-specialist reliability proof — logged as a `BACKLOG` evidence gap
(`AGT-005`), a prerequisite before Wave 7 is called production-ready, not satisfied here.
