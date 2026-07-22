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

## Responsibility Boundaries

### Product Agents

The individual product agents will continue to provide accurate, product-specific information,
including:

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

## Pilot and Research Approach

I will begin by applying this approach to a small group of FOSS repositories as a pilot. I will
further study n8n and other leading FOSS projects, together with our strongest NuGet product
pages, to understand what makes their product presentation effective.

Each repository will then be improved according to its own purpose, users, and capabilities
rather than by copying a common template.
