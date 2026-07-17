# foss-readme-optimizer

An audit-and-remediation agent for Aspose's FOSS GitHub repositories: it detects specific missing
promotional elements in a README (license mention, `products.aspose.org`/`products.aspose.com`
links, an explanation of the FOSS-vs-commercial relationship) and proposes a bounded, policy-
controlled fix — closing only what's actually missing, never rewriting existing content. Every run
is local-first and push-blocked: target repos are cloned into disposable working copies with their
push remote neutered and a pre-push hook installed, so nothing is ever pushed to a real remote by
this tool. See `docs/architecture.md` and `docs/safety-model.md` (once written) for details.

**License**: not yet decided — no `LICENSE` file exists in this repository yet. All rights
reserved by default until a license is chosen.

## Quick start

```
pip install -e ".[dev]"
readme-agent preflight
readme-agent run --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Java --mode dry_run
```

See `.env.example` for required environment variables.
