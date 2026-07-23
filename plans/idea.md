# Central Repository-Presentation Agent

## Core Principle

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

Links to Aspose and the related commercial product should then be included naturally where they
provide useful context.

## Lessons From Existing Repositories

### n8n

I reviewed the n8n repository with this principle in mind. The main lesson is not to copy its
structure or sections, but to make the README, repository information, visuals, releases,
packages, and supporting files work together to present one clear and credible product.

Some of these elements can be managed directly:

- README;
- repository description;
- website;
- topics;
- visuals;
- community files;
- releases; and
- repository settings.

Other elements are generated automatically by GitHub:

- contributors;
- languages;
- activity;
- stars; and
- forks.

The agent can audit these generated elements and investigate unexpected results, but it cannot
directly control how GitHub displays them.

### Aspose FOSS Repositories

For context, the recent changes to the Aspose.3D FOSS for Python README were made by
bot. They were not produced by the proposed central agent and do not represent the intended
quality standard. However, the result shows why stronger shared standards and review controls are
needed.

I have also reviewed the existing FOSS repositories and found considerable variation in how they:

- describe the products;
- structure the READMEs;
- present examples; and
- link back to Aspose.

Because these repositories are maintained through different product agents and publishing
workflows, a one-time cleanup would not be enough. Later automated updates could otherwise
overwrite or weaken the improvements.

## Proposed System

The goal is to create a central repository-presentation agent rather than a simple README
rewriting agent.

### Operating Model

This will be an autonomous system that:

- continuously monitors the GitHub repositories listed in `data/products.json`;
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
expressed as explicit rulesâ€”including control flow, safety checks, state management, caching,
idempotency, validation, and repeatable transformationsâ€”should be implemented deterministically.

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

I will begin by applying the core repository-presentation approach to a small group of FOSS
repositories as a pilot. Full visual-asset and social-preview delivery is outside the initial
pilot's required scope, but remains part of the intended autonomous system.

I will further study n8n and other leading FOSS projects, together with our strongest NuGet
product pages, to understand what makes their product presentation effective.

Each repository will then be improved according to its own purpose, users, and capabilities
rather than by copying a common template.
