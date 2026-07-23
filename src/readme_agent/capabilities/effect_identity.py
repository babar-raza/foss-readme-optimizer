"""Wave 9.6 (`EFF-006`): fixes a confirmed live bug, not a hypothetical one.
`effect_ledger.py::idempotency_key()` previously hashed only `org_repo` +
`facts_hash` + `fresh_fingerprint`, where `fresh_fingerprint`
(`readme/facts.py::compute_tracked_content_hash()`) is the PRE-RENDER
upstream baseline hash -- computed by `orchestrator.py::
prepare_readme_candidate()` before the LLM ever runs -- never a hash of the
rendered candidate/`final_text` itself. Two different generated candidates
against the same unchanged upstream (`force_regenerate=True` combined with
ordinary LLM sampling variance in the `relationship_explained` paragraph, or
a repaired candidate produced after a verifier rejection) collided on the
exact same idempotency key: `effect_ledger.py`'s own `already_applied`
cache-hit logic would then silently discard the second, newly-verified
candidate in favor of the first, stale one.

`EffectIdentityV1.candidate_byte_hash` is the one field that actually
distinguishes two different rendered candidates -- the field this whole
fix exists to add. Everything else here is reused, not recomputed:
`readme/facts.py::compute_facts_hash()` already folds `policy_content_hash`/
`prompt_content_hash`/`GENERATION_SCHEMA_VERSION`/`VALIDATION_RULESET_
VERSION` into `facts_hash` -- naming those components again as separate
fields here would not add any discriminating power `facts_hash` doesn't
already have, so `product_facts_hash` below reuses `facts_hash` wholesale
rather than re-deriving its already-folded-in components."""

import hashlib
import json

from pydantic import BaseModel


class EffectIdentityV1(BaseModel):
    effect_type: str
    org_repo: str
    upstream_surface_hash: str
    candidate_byte_hash: str
    product_facts_hash: str

    def canonical_json(self) -> str:
        dumped = self.model_dump(mode="json")
        return json.dumps(dumped, sort_keys=True, separators=(",", ":"))


def compute_candidate_byte_hash(final_text: str) -> str:
    return hashlib.sha256(final_text.encode("utf-8")).hexdigest()


def build_effect_identity(
    *,
    effect_type: str,
    org_repo: str,
    facts_hash: str,
    fresh_fingerprint: str,
    final_text: str,
) -> EffectIdentityV1:
    return EffectIdentityV1(
        effect_type=effect_type,
        org_repo=org_repo,
        upstream_surface_hash=fresh_fingerprint,
        candidate_byte_hash=compute_candidate_byte_hash(final_text),
        product_facts_hash=facts_hash,
    )
