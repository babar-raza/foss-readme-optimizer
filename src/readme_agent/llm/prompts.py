"""build_prompt(facts, policy) -- and *only* those two already-hashed objects.

No ambient reads, no side-channel parameters. This is the mechanical half of
the facts<->prompt coupling fix (Consistency & Determinism Tier 1 SS2):
tests/unit/test_prompt_hash_coupling.py asserts both the signature stays this
narrow and that every field expected to matter actually changes the output.

Prompt content is loaded from a categorical, schema-validated registry
(llm/prompt_registry.py, GOV-024, Wave 8.5) rather than raw .txt files -- see
prompts/generation/relationship_explained.yaml. prompt_content_hash() stays
narrowly scoped to this one file (not the whole registry) since it feeds
RepositoryFacts._HASH_FIELDS/compute_facts_hash() -- widening it would make
any unrelated prompt edit (e.g. the supervisor planner's own prompt) force
every README to look stale. It reads the file fresh on every call (never
routed through the eager, import-time-cached prompt_registry), matching this
function's own long-standing "always current" contract. The whole-registry
hash lives separately at prompt_registry.content_hash(), consumed by
supervisor/convergence.py::compute_control_plane_fingerprint() instead.
"""

from pathlib import Path
from string import Template

from readme_agent.llm import prompt_registry
from readme_agent.readme.facts import RepositoryFacts, sha256_text
from readme_agent.registry.models import PolicyProfile

PROMPT_ASSET_PATH = Path("prompts") / "generation" / "relationship_explained.yaml"


def prompt_content_hash() -> str:
    return sha256_text(PROMPT_ASSET_PATH.read_text(encoding="utf-8"))


def build_prompt(facts: RepositoryFacts, policy: PolicyProfile) -> list[dict[str, str]]:
    org_link = policy.required_elements.products_org_link
    com_link = policy.required_elements.products_com_link
    element = policy.required_elements.relationship_explained
    manifest_name = facts.manifest.get("name") or facts.manifest.get("artifact_id") or "unknown"

    manifest = prompt_registry.get("relationship_explained")
    assert manifest is not None and manifest.user_template is not None, (
        "prompts/generation/relationship_explained.yaml must be registered with a user_template"
    )

    system = manifest.system.strip()
    user = (
        Template(manifest.user_template)
        .substitute(
            org_repo=facts.org_repo,
            manifest_name=manifest_name,
            detected_license=facts.detected_license or "not detected",
            org_link_label=org_link.label,
            org_link_url=org_link.url,
            com_link_label=com_link.label,
            com_link_url=com_link.url,
            min_sentences=element.min_sentences,
            talking_points=", ".join(element.talking_points),
        )
        .strip()
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
