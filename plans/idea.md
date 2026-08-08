# Central Repository-Presentation Agent

## Core Principle

This document owns the permanent product outcome and operating intent. Authority is otherwise
domain-specific: `plans/requirements.md` owns normative acceptance; `plans/master.md` owns
architecture, decisions, sequencing, and rollout; `plans/GOVERNANCE.md` and `AGENTS.md` own
editing, safety, execution, and coordination; the Level-8 mission graph is the sole
machine-readable task/dependency graph; durable supervisor state owns live claims, transitions,
and runtime status. Supporting plans, roadmap, status, reports, audits, and handovers are derived
guidance/evidence and cannot override their owning authority.

The issue is not only where links to `aspose.org` and `aspose.com` are placed. A FOSS
repository must first establish the product as useful, credible, and professionally maintained.
When promotional links appear before the product has clearly explained its value, they can reduce
trust rather than strengthen the connection with Aspose.

The product should therefore come first. A visitor should be able to understand quickly:

- what the library does;
- which problems it solves;
- which features and formats it supports;
- how to install and use it; and
- whether it is actively maintained.

Links to Aspose and the related Enterprise Edition should then be included naturally where they
provide useful context. Every visitor-facing reference to an `aspose.com` product uses
**Enterprise Edition** as its edition name—never “commercial edition,” “On-Premise edition,”
“paid version,” “full version,” or another substitute. “Context” means direct reader utility in
the surrounding content: when a
README shows a code example, format workflow, command, or API, a verified documentation, knowledge
base, or reference article that explains that exact material may be linked in the adjacent prose.
A generic product page is not a contextual substitute for a more useful exact article. If no
verified target directly helps with the nearby content, the natural result is no link.

Aspose-link density must adapt to the README rather than follow a universal quota. Repository
policy may explicitly configure maximum total, `aspose.org`/`aspose.com`, and
`products`/`docs`/`kb`/`blog`/`reference` slots. When it does, those configured maxima replace the
automatic allocation. Otherwise the system derives conservative maxima deterministically from
the README's visible content size and verified code examples. Every slot is a ceiling, not a
target; configuration or available capacity never justifies an irrelevant, unverified, repetitive,
awkward, or promotional link.

## Portfolio README Presentation Contract

The portfolio uses one assurance-neutral visual and structural contract. It is a brand shell, not a
universal prose template: trusted and verified lanes share the same visitor experience, while each
repository supplies its own product facts, formats, capabilities, examples, limitations, and
maintenance material.

Every README has exactly one factual H1 and one compact badge row in a stable order: package or
release, platform/runtime, real build status, license, then contributors when those slots are
supported. Badges may be omitted when their claims or targets are unavailable, but they may not be
duplicated, split across multiple header rows, or fabricated merely to fill the row. The opening
explains the FOSS product before any Aspose promotional destination.

Every visitor-facing product-identity position uses the complete canonical product name, including
the H1, opening, Mermaid product node, metadata proposal, visual labels, and relationship prose.
Package names, import paths, namespaces, commands, and API identifiers may use their exact technical
forms only where that technical identifier is itself the subject. A package or namespace shorthand
must never replace the product name merely to save space.

The common visitor journey is product explanation, compact list-based navigation, a product-specific
`At a Glance`, capabilities, installation, a visible minimal example, additional examples, API
reference when useful, scope and limitations, development/contribution material, and a prose
license declaration. When a third-party-notices file exists, it receives its own visitor-visible
heading and a correct repository-relative link whose label uses normal link text rather than
inline-code styling. The license is never presented as a bare link; a
permissive license such as MIT briefly explains its practical permissions and notice condition
without replacing the authoritative license text. A README-level copyright line
is omitted by default because the repository license owns that declaration; a portfolio policy may
enable it only when the same verified owner and formatting rule applies consistently.

Every Markdown heading uses title case. Visitor-facing technical abbreviations use their canonical uppercase forms throughout, including PS, EPS, PDF, XPS, XLSX, HTML, and equivalent discovered formats or protocols. Exact package names, paths, imports, namespaces, API members, commands, and link destinations retain their source spelling. The renderer derives terminology from accepted facts plus the governed technical registry; validation rejects noncanonical public casing.
`At a Glance` is a typed semantic capability graph, not an implied runtime pipeline. It separates inputs, the complete product, a Core capabilities group whose feature nodes use one vertical column for at most five entries and two balanced vertical columns above five, and verified outputs. Inputs connect to the product; exactly one visible undirected relationship connects the product to Core capabilities, and one connects Core capabilities to Outputs when outputs exist. Individual capabilities do not fan out to the product or outputs. Selector parameters are not inputs, intermediate structures are not outputs, and delivery methods are not formats; misleading topology fails even with valid syntax.

GitHub-compatible `<details>` keeps long documents readable while installation, the minimal example,
core capabilities, important limitations, and top APIs remain visible. Secondary material may be
collapsed without dropping, rewriting, or approving inherited content. Additional-examples prose previews the named workflows a visitor can expand; it never exposes internal inventory, source-revision, syntax-check, static-API-check, or non-execution commentary. Every expanded workflow uses a meaningful task name rather than a duplicated generic heading with a numeric suffix. Key-capability titles are natural action-led search phrases grounded in accepted product, platform, input-format, and output-format facts without keyword stuffing. Omit redundant “Other
platforms” or promotional sections that add no reader utility.
Internal assurance narration never appears in the public README. Source revisions, isolated-build conditions, network policy, registry receipts, provider calls, evidence collectors, and validation status belong in evidence; the README states only the useful public consequence, such as installing from source when no verified package command is available. Aspose.com product links use natural explanatory prose and an informative **full-featured ... Enterprise Edition** anchor below the fold. Competing sections may not repeat the same capability inventory.
Maintainer-authored source README information is valuable evidence, not disposable text and not automatically true. Once reconciled, it is preserved or tuned inside the relevant canonical section such as Key Capabilities, Installation, Additional Examples, API Reference, Documentation and Resources, Scope and Limitations, or Development and Testing. The system must never expose generic implementation labels such as “Preserved repository details.” Material detail with no safe semantic destination fails closed for upstream reconciliation rather than being dumped into the document.
The manually composed Note reference is a structural seed, not the ceiling. Its same-revision
Aspose.org comparison is development-only and exposes missing native extraction, selection,
composition, graph, and review behavior that must become self-contained Repo Presenter contracts.
Production and acceptance cannot read sibling assets; Note must regenerate independently.

The composer creates a coherent developer journey, not a fact inventory: precise opening, one badge
row, navigation, semantic graph, task-oriented capabilities, acquisition, executed example, curated
hub APIs, destinations, limitations, and maintainer guidance. Review rejects unhelpful presentation.

## Production-Readiness Standard

The solution must be production-grade and production-ready by the time it reaches at least the
agreed 7/8 maturity threshold. At that point, the system must demonstrably perform the complete
operating model described in this document under real production conditions. A prototype,
collection of disconnected capabilities, or system that works only through routine manual
intervention does not meet this standard.

Production readiness does not require every possible enhancement to be complete. It allows a
small number of known, bounded, non-critical issues to remain, provided they are documented and do
not prevent autonomous, reliable, safe, and idempotent operation. No core obligation described in
this document may remain merely aspirational at that threshold.

README health is the foundational goal. The system must be able to assess, update, reconstruct
when necessary, and continuously improve repository READMEs using verified repository facts. This
baseline outcome is non-negotiable and must not be displaced by broader presentation features,
research work, or infrastructure development. It must be achieved while preserving the system's
truthfulness, safety, verification, and repository-protection requirements.

That core deliverable is the immutable mission outcome and closure standard. It is not a universal
runtime goal. Execution uses the ordered stage goals defined below so the agent always sees the
next concrete outcome rather than a generic mission label. No stage may become a stopping point
merely because its machinery, tests, or evidence exist.

## README POC Readiness and Ordered Delivery Gates

The POC is the full currently eligible, discoverable authorized portfolio, not a sample and not
merely a stale checked-in list. `data/products.json` remains the hard execution allow-list and its
exact admitted count is computed at runtime (`len()` over its entries), never hard-coded. Gate-A
closure also requires a fresh, complete discovery reconciliation: every repository visible from
each authorized source has an explicit observation and disposition; pending intake, unexplained
observations, source failures, and stale scans are zero. Eligibility is fail-closed and
case-insensitive: a repository name must have exactly the form
`Aspose[.-]{Family}-FOSS-for-{Platform}`, with one terminal platform token and no trailing variant
suffix. Both `Aspose.PDF-FOSS-for-Go` and `aspose-pdf-foss-for-go` qualify; `CSSForge` and
`Aspose-PDF-FOSS-for-Go-MCP` remain visible discovery exclusions and never enter the execution
allow-list. A newly observed eligible repository is admitted automatically only as disabled/read-only
and enters the same preflight and README lifecycle. A naming mismatch never makes an observation
invisible, but it prevents admission. A result covering only part of the admitted registry, or a
registry whose source inventory is incomplete, is a development batch or partial result and is
never presented as "the POC."

### Current delivery-first verified Python proving milestone

The temporary trusted lane is preserved but no longer executes. Its README-derived extraction,
LLM composition, targeted repair, cache, retry, lease, workflow, staging, App, and effect evidence
remain reusable only within their proven assurance boundary. They never become repository facts
or verified acceptance merely through reuse.

The project remains **pre-POC** until one current repository completes the entire verified
lifecycle. Machinery, facts, candidates, deterministic validation, historical approval, and a
golden sample do not change that classification. The first visible milestone is one finalized
verified README; it is not itself a platform POC. The first platform POC is Python and closes only
when every runtime-loaded Python repository completes the same current contract.

Execution is delivery-first but its mutable cursor never lives in this product document:

1. mission `evaluate` reconciles graph drift, claims, lifecycle freshness, and component hashes;
2. mission `status` selects one typed immediate goal, repository scope, and next action from the
   earliest dependency-ready or regressed boundary;
3. that repository completes facts, composition, deterministic validation, independent review,
   targeted repair, unchanged no-op, promotion, and manifest reconstruction before its task closes;
4. feedback creates a component delta and reruns only dependent stages; historical closure cannot
   satisfy a changed factual, safety, protected-content, or severe acceptance contract;
5. the same loop completes the dynamic Python denominator, then .NET, Java, C++, TypeScript, Rust,
   and Go, followed by verified Gate A/B/C and production deployment;
6. Level-7 and Level-8 elapsed observations run only as background certification after deployment.

The Level-8 mission graph owns the stable repository-focus chain. Durable mission state alone says
which member is current. Narrative documents may describe stage order but must never override or
duplicate that cursor.

At each boundary, terminology is fail-closed: one finalized repository is the **first verified
README**, all current Python repositories are the **verified Python platform POC**, and all current
admitted repositories are **verified Gate A**. A smaller numerator must be reported as partial
progress with its exact denominator.

### Agile operating model

The presentation design is intentionally agile. **Versions freeze; the design does not.** Every
repository transaction pins immutable component versions for reproducibility, while later changes
create new versions and migrate only affected sections. Component identities cover title/identity,
badges, opening, navigation, Mermaid, installation, examples, capabilities/formats, documentation,
community, license, Enterprise Edition relationship, contextual links, and density. Cosmetic,
structural, prose-policy, fact-slot, factuality/safety, and major-document changes have distinct
invalidation scopes. A non-critical later template version leaves an accepted README
`VALID_UPDATE_AVAILABLE`; only factual, safety, protected-content, or severe acceptance defects
make it invalid. Portfolio reporting separates fact-valid, presentation-valid, latest-version,
human-accepted, and publication-eligible counts.

Human acceptance is staged. Comparative Aspose.Note FOSS for Python is the first calibration output
and accepted-structure reference; Aspose.3D follows, then Page/PDF complete the representative
Python cohort. Human feedback may revise the component
contract without erasing unrelated facts or accepted work. Remaining repositories continue
autonomously after representative-cohort acceptance. No product-repository proposal is eligible
until every admitted repository is locally valid and explicitly human-accepted in the indexed
portfolio Gate B.

Infrastructure is just-in-time. A task enters the active path only when it unblocks the current
repository, will be exercised by the next bounded cohort, fixes a demonstrated safety/factuality/
reproducibility defect, or measured repetition proves a net benefit inside the current cohort.
Otherwise it is deferred. One infrastructure task at most may sit between visible README delivery
tasks before Python closes. New ecosystem support begins with one serial representative and earns
parallelism only after the transaction is stable.

Verification is risk-based: touched static/focused checks, impacted integration/safety proof,
complete non-live suites at shared-code or declared stage boundaries, mandatory per-repository
facts/candidate/validation/independent-review/no-op proof, and one aggregate cohort reconstruction.
Mutable failures stay under `runs/`; canonical evidence is promoted once per repository and cohort,
not per micro-fix.

The coordinator is the only operator and shared-state owner. The calibration transaction and shared
repairs are serial; a non-authoring independent verifier remains mandatory. After isolation proof,
two representative and then at most three disjoint repository workers may run with separate state
and evidence plus serialized aggregation. Delegation is admitted only when measured throughput
improves; mandatory five-role ceremony is prohibited.

Elapsed maturity is certification, not delivery work. Production-ready and production-deployed are
executable milestones. Level 7 and Level 8 observation periods are configurable background tracks
started only after deployment; they never block POC, portfolio acceptance, staging, or deployment.
`delivery_complete` closes executable work through deployable Level 6; `certification_complete`
closes Level-7/8 observation and audit. Full mission closure requires both.

The agent treats user input as goals, constraints, preferences, hypotheses, tactics, or authority.
Goals and constraints bind; tactics and hypotheses are evaluated. Before a material route change,
the agent checks critical-path, invalidation, infrastructure timing, safety, factuality, and smaller
alternatives, and challenges an inefficient or conflicting tactic with evidence. Two equivalent
failed attempts or 15 minutes without material narrowing require a first-principles review and a
different causal boundary or mechanism. Clear safe implementation continues autonomously.

`plans/idea.md` is the human product authority. Agent-owned authority must be compact and loaded by
need: a concise `master.md`, a typed requirement catalog queried only for the current task and
always-on invariants, an executable graph containing at most 15 current/near-term tasks and five
ready tasks, and durable state as live truth. Detailed history remains in Git/logs; derived
handovers never override live state. The authority reset precedes further product execution and is
bounded to migration, validation, and one coherent commit.

Two ineffective attempts with one approach fingerprint, or 15 minutes without a materially
narrower result, prohibit another equivalent attempt. Before a third approach, the agent records
a first-principles review and changes the causal owner, pipeline boundary, or mechanism. Unchanged
source, facts, template, prompts, policy, validators, reviewer standard, protected-content
fingerprint, and runtime reuse sealed results; a changed dependency reopens only its downstream
stages. These speed controls never weaken factuality, validation, independent review, safety, or
evidence.

`verified_repository_presentation` is the only executable content-assurance horizon. It derives
mechanically testable facts from repository source, manifests, public consumer surfaces, tests,
examples, releases, and approved external authorities; reconciles inherited README claims; and
governs every presentation surface. The historical `trusted_readme_transform` lane is suspended.
Its code, tests, caches, retries, leases, workflow/staging/App/effect proof, and lessons may be
reused only behind verified contracts and within their demonstrated boundary. Trusted facts,
candidates, verdicts, no-op evidence, proposals, and PRs never satisfy verified acceptance.

The mission outcome is immutable, but it is not an always-active execution goal. The supervisor
derives the primary verified goal from the earliest incomplete accepted gate and persists it with
the task claim. It may derive concurrent dependency-ready read-only work within the goal's capacity
policy. Historical trusted goals are inspectable with `execution_required: false`; they receive no
claim, capacity, or effect authority. Evidence-backed closure advances goals automatically; a
regression, invalidated dependency, or newly admitted repository reactivates the earliest affected
goal. Safety, factuality, authorization, evidence, and idempotency remain always-on acceptance
invariants.

Delivery proceeds through ordered gates, and a later gate never starts before the gate it depends
on is actually accepted, not merely attempted:

1. **Historical trusted proof — preserved, non-executable.** T0, TP, T0R, T1, T2, and T3 records
   remain forensic evidence and reusable implementation inputs only. They are not active gates,
   do not reserve capacity, cannot be selected or claimed, and cannot satisfy any verified
   acceptance. No trusted candidate, review, no-op, proposal, or PR may be resumed as mission work.
2. **Common Gate C0 — complete authorized-portfolio discovery and intake.** Inventory every
   repository visible from every explicitly authorized source using authenticated all-visibility
   pagination. Record public, private, internal, archived, unmatched, ambiguous, inaccessible,
   renamed, and transferred observations by stable provider identity. Every active product
   repository is admitted as disabled/read-only and receives exactly one durable preflight; every
   exclusion is explicit and evidence-backed. Zero unexplained observations, source failures,
   stale scans, or pending intake are required for portfolio completeness. Read-only intake may
   advance concurrently when dependency-ready.
3. **Gate A — full-registry verified local README proof.** Repository-verified discovery, facts,
   reconciliation, and candidate work is the exclusive active presentation path. Gate A closes
   only from complete repository-verified evidence. For every registry repository, the system reads
   the README from the repository's current default branch, records the source revision and exact
   original bytes, assesses that README against this document, verifies product facts against the
   repository and relevant package/platform evidence, and produces a repository-specific enhanced
   README candidate locally. The original README, candidate, diff, facts, plan, validation results,
   and review verdict remain reviewable local artifacts. Read-only GitHub access needed to obtain
   this evidence is part of Gate A; remote writes, pull requests, and GitHub App integration are
   not.
4. **Independent agentic approval completes the system portion of Gate A.** Every candidate passes
   deterministic factuality, claim-accountability, preservation, structure, links, safety, and
   golden-contract gates, then one independent non-authoring evidence-grounded reviewer. A second
   reviewer runs only for a typed risk trigger proven by the regression corpus. The system is ready
   for POC human review only when every entry in the current complete registry revision has an
   agent-approved, no-op-proven local candidate and intake is fully reconciled. A candidate file
   merely existing is not approval. A strong existing README may take a fast path, but still needs
   verified inherited claims, deterministic assessment, an empty-patch candidate, independent
   approval, and no-op proof.
5. **Gate B — verified human review follows agent approval.** Humans review only candidates that already
   passed independent agentic review. Human acceptance is recorded separately; it is not inferred
   from an agent verdict. Every registry candidate must be human-accepted before Gate C begins.
6. **Gate C — verified Java proposal proof follows full local and human acceptance.** Historical
   trusted PRs do not satisfy this gate. Creating or updating verified proposals against the designated
   Java repositories is attempted only after every current registry repository has passed Gates A
   and B, not before. Gate C reuses the already qualified App/workflow/effect machinery and proves
   that repository-verified candidates, authorization, and proposal semantics work at the higher
   assurance. Prior transport proof is reusable only when its exact dependencies remain current.

Standing constraints apply across every gate:

- **The existing README is a high-value, product-agent-curated source to reuse wherever
  validation permits—not unquestioned truth and not disposable input.** The product-development
  agent may have recorded important capabilities, limitations, examples, terminology, workflows,
  and maintainer intent that other sources do not express as clearly. The system must inventory
  every material content unit and seek to preserve or improve it, but each unit must first be
  validated against accepted repository/package evidence or an authoritative owner. Verified
  content is reused; stale or contradicted content is corrected with evidence; unresolved content
  is omitted or carried as explicit uncertainty for owner resolution. Regeneration convenience is
  never a reason to discard valuable curated information. Historical trusted-lane inheritance may
  help locate content but never satisfies this verified rule.
- **LLM/agentic reasoning is required for repository interpretation and composition.** Understanding
  what a repository's product actually does, who it is for, and how to present it credibly is a
  judgment task no fixed rule set can fully express. Deterministic code supplies safety,
  validation, and verification around that judgment — it does not substitute for it. A candidate
  produced by phrase-matching or template-filling alone, with no genuine interpretive reasoning
  behind it, does not satisfy this standard even if it passes every deterministic check.
- **Every LLM interaction is attributable to the README it helped produce.** Production evidence
  records every attempted provider call and cache reuse by repository, immutable source revision,
  lifecycle stage, job, prompt ID/hash, model, retry attempt, outcome, latency, and token usage
  when the provider reports it. Per-README and portfolio totals must reconcile with the underlying
  call records. An unchanged no-op may reuse accepted results but must make zero new provider
  calls for those unchanged jobs.
- **Prompt assets remain a small governed registry, not an accumulating scratch directory.** Every
  runtime prompt has one owner, one job/consumer, one schema-validated manifest, and one dependency
  hash. Unknown, duplicated, orphaned, deprecated-without-replacement, or executable-inline prompts
  fail the official inventory check before another paid portfolio campaign.
- **Product and platform decisions belong to the system.** The system detects the product,
  ecosystem, repository shape, and available evidence, then selects the appropriate capabilities,
  facts, sections, examples, and validation paths itself. A normal run does not require a human to
  choose a product-specific template, capability, skill, or command sequence.
- **Ecosystem truth includes the package's public consumer surface, not only its manifest.** Python
  imports and exported symbols, TypeScript package exports and declarations, and Rust visibility,
  modules, and re-exports must be proved before examples or capability claims are accepted. The
  committed extraction modules and regressions in the sibling `aspose.org` pipeline are a
  development-only reference. Any lesson must be reimplemented behind this project's contracts;
  staging, deployment, and acceptance cannot read or depend on sibling assets.

Battle-tested, proven tools and libraries are preferred over new custom infrastructure. Building a
bespoke mechanism where an established one already solves the problem requires a documented reason
— naming the proven alternative considered and why it was not used — not a silent default choice.

## Lessons From Existing Repositories

Leading FOSS repositories such as n8n show that README, metadata, visuals, packages, releases,
and community files must present one coherent product; their exact sections are not templates to
copy. Repository-owned surfaces may be proposed or changed through their governed owner, while
GitHub-generated contributors, languages, activity, stars, and forks are observations only.

Aspose FOSS repositories currently vary in product explanation, README structure, examples, and
link placement. Existing bot-produced README changes are evidence and reusable input, not the
quality standard. Because product agents and publishing workflows continue to update repositories,
the solution must be a durable central control with drift detection and protected content—not a
one-time cleanup.

## Proposed System

The goal is to create a central repository-presentation agent rather than a simple README
rewriting agent.

### Operating Model

This will be an autonomous system that:

- continuously inventories explicitly authorized GitHub sources, reconciles `data/products.json`,
  and monitors every admitted repository, including newly discovered read-only entries;
- runs at regular intervals or in response to specific triggers;
- performs the repository-presentation work described below without routine human intervention;
- maintains the caches, persistent state, and idempotency controls required for reliable
  operation; and
- includes any other operational safeguards needed to run robustly over time.

Humans will periodically review its work, but their role will primarily be passive oversight
rather than operating the system or initiating its routine work.

### Execution Environments and GitHub Access

Local testing will use a local GitHub Actions-compatible runner to reproduce the production
workflow as closely as practical before changes are exercised on GitHub. Production workloads
will run on actual GitHub Actions runners in the configured production workflows.

GitHub authentication will be environment-specific:

- local testing will use the operator-provided `GH_TOKEN` environment variable; and
- production will use a dedicated GitHub App and its short-lived installation access tokens.

Workflow behavior should remain consistent across local and production execution, while the
credential provider stays explicit and isolated behind the GitHub access boundary. Credentials
must never be embedded in workflow definitions, source code, caches, state, logs, or evidence.
Production must fail closed if GitHub App authentication is unavailable; it must not silently
fall back to a personal access token or local-development credential.

## Implementation Principles

### Deterministic and Agentic Approach

The system must combine deterministic and agentic approaches. Responsibilities that can be
expressed as explicit rules—including control flow, safety checks, state management, caching,
idempotency, validation, and repeatable transformations—should be implemented deterministically.

Agentic reasoning should be used where interpretation, planning, editorial judgment, or adaptation
to repository-specific context is genuinely required. Agentic outputs must remain subject to
deterministic validation and operational safeguards before they produce an effect.

### Prefer Battle-Tested Solutions

Development should favor battle-tested libraries, frameworks, standard facilities, and proven
reference implementations over hand-rolled solutions. Existing solutions should be actively
researched and evaluated before custom functionality is developed.

This preference is intended to accelerate development, reduce maintenance risk, and make
troubleshooting easier by building on tools and patterns that have already been exercised in real
systems. A custom solution should be used only when the proven alternatives do not satisfy the
system's requirements and the reason for departing from them is documented.

## Responsibility Boundaries

### Trust and Repository-Grounded Reconciliation

Content supplied by a product agent, injected by an automated workflow, or already present in a
README must be treated as an input to investigate, not as trusted truth. This applies equally to
content maintained before the central agent was introduced.

The central agent must independently reconcile product claims against evidence available from the
repository, including its source code, manifests, configuration, examples, tests, documentation,
license files, commit history, tags, and releases. Product-agent output may help locate relevant
facts, but it must not override contradictory repository evidence or become the sole basis for a
published claim.

The agent must improve presentation using only claims that the repository evidence supports. It
must correct or remove inaccurate, stale, contradictory, generic, or unsupported statements. When
the available evidence cannot establish a claim, the agent must preserve the uncertainty and flag
the gap for review rather than inventing, assuming, or presenting the claim as fact.

### Product Agents

The individual product agents will continue to provide product-specific information for the
central agent to reconcile, including:

- features;
- supported formats;
- installation instructions;
- APIs;
- examples; and
- release changes.

They are better placed to provide these technical details.

### Central Agent

The central agent will review how the product-specific information is presented and apply a
consistent quality standard across the FOSS repositories. Its responsibilities will include:

- improving the README and repository description;
- maintaining the website, topics, visuals, and social-preview image;
- checking community, contribution, licensing, and security files;
- reviewing releases and package links where applicable;
- ensuring that links to Aspose are relevant, naturally placed, and not overly promotional;
- preventing automated product updates from replacing strong content with generic or
  inconsistent text; and
- auditing GitHub-generated information without treating it as directly editable metadata.

### Visual Assets and Social Preview

Visual-asset and social-preview preparation is part of the central agent's intended responsibility,
but it is not required to be fully delivered during the initial pilot. Repository-owned visual
assets may be proposed through the normal bounded file-change lifecycle. A social-preview image is
a manual-UI surface unless and until GitHub provides a documented, supported automation mechanism.

During an interim phase, the agent may prepare a validated asset and a precise handoff when no
safe, supported automation mechanism is available. That handoff is a bounded fallback, not the
target operating model.

The preparation capability must be autonomous and idempotent like the rest of the system. It must
derive assets from verified repository facts, track desired and observed asset state, avoid
regenerating or redelivering an unchanged asset, detect drift, and produce exact manual-application
evidence where GitHub exposes no supported write interface. It must never claim that a social
preview was applied merely because an asset was prepared. Human involvement remains passive
oversight except for surfaces that are genuinely manual-UI-managed.

## Pilot and Research Approach

Implementation may prove a mechanism on small, explicitly labeled development batches before
scaling it. Those batches are risk-control steps, not the README POC and not substitutes for
full-registry Gate A/B evidence. Full visual-asset and social-preview delivery is outside the
README POC's required scope, but remains part of the intended autonomous system.

Further research will study n8n and other leading FOSS projects alongside the strongest Aspose
NuGet product pages to identify what makes their product presentation effective.

Each repository will then be improved according to its own purpose, users, and capabilities
rather than by copying a common template.
