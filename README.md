# foss-readme-optimizer

An autonomous, capability-driven repository-presentation system: it understands a product
repository, decides which GitHub presentation surfaces are relevant, and keeps them credible and
repository-specific — never a generic template. The Aspose FOSS portfolio is its first deployed
product profile, not the ceiling of what it addresses (see `plans/master.md`'s Mission and
Decision #26 for the full target architecture).

[`plans/idea.md`](plans/idea.md) captures the core product idea and intended operating model.
`plans/master.md` remains the authoritative executable specification for turning that idea into
the governed system.

**Current objective**: every repository listed in `data/products.json` (count computed at
runtime, never hard-coded) reaching an independently agent-approved, no-op-proven local README
candidate derived from its current default-branch README — full-registry local README management,
not just patching a fixed set of promotional elements. Only then are the candidates ready for
human review. Java pull-request proof is gated behind full-registry human acceptance, and broad
GitHub App integration is gated behind the Java proof. See `plans/idea.md`'s "README POC Readiness
and Ordered Delivery Gates" section for the full ordering.

**Current stage**: `supervise` is the sole production runtime (`readme-agent supervise`) —
observe → plan → execute → verify against the capability registry. `generate`, `run`, and
`run-registry` are read-only/compatibility façades, not alternate mutation paths. Dynamic,
product/platform-aware capability selection is the required canonical local behavior, but it is
still an honest open gap: `--enable-dynamic-planning` remains opt-in today. The original
deterministic promotional-element audit remains the most mature capability; it is not the full
README-management POC. The `local_poc` profile keeps work in push-neutered local clones and
disallows `remote_write`. A separately gated PR capability exists from earlier development, but it
must not be used again until the full-registry local and human-acceptance gates are satisfied. See
`docs/architecture.md` and `docs/safety-model.md` for details.

**License**: not yet decided — no `LICENSE` file exists in this repository yet. All rights
reserved by default until a license is chosen.

## Quick start

```
pip install -e ".[dev]"
readme-agent preflight
readme-agent supervise --registry data/products.json --execution-profile local_poc
```

See `.env.example` for required environment variables.
