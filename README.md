# foss-readme-optimizer

An autonomous, capability-driven repository-presentation system: it understands a product
repository, decides which GitHub presentation surfaces are relevant, and keeps them credible and
repository-specific — never a generic template. The Aspose FOSS portfolio is its first deployed
product profile, not the ceiling of what it addresses (see `plans/master.md`'s Mission and
Decision #26 for the full target architecture).

The **currently shipped engine** — what actually runs today — audits a repository's README for
specific missing promotional elements (license mention, `products.aspose.org`/
`products.aspose.com` links, an explanation of the FOSS-vs-commercial relationship) and proposes a
bounded, policy-controlled fix, closing only what's actually missing and never rewriting existing
content. It's the first capability surface the target runtime will wrap, not something being
discarded. Every run is local-first and push-blocked: target repos are cloned into disposable
working copies with their push remote neutered and a pre-push hook installed, so nothing is ever
pushed to a real remote by this tool. See `docs/architecture.md` and `docs/safety-model.md` for
details.

**License**: not yet decided — no `LICENSE` file exists in this repository yet. All rights
reserved by default until a license is chosen.

## Quick start

```
pip install -e ".[dev]"
readme-agent preflight
readme-agent run --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java --mode dry_run
```

See `.env.example` for required environment variables.
