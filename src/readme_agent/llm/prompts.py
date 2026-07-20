"""build_prompt(facts, policy) -- and *only* those two already-hashed objects.

No ambient reads, no side-channel parameters. This is the mechanical half of
the facts<->prompt coupling fix (Consistency & Determinism Tier 1 SS2):
tests/unit/test_prompt_hash_coupling.py asserts both the signature stays this
narrow and that every field expected to matter actually changes the output.

Prompt text itself lives in prompts/relationship_explained/ (prompts/README.md
rule 1/3) -- loaded here, never embedded as a string literal. prompt_content_hash()
lets callers fold the loaded file content into the generation hash, so an
edited prompt file forces regeneration instead of silently reusing a stale one.
"""

from pathlib import Path
from string import Template

from readme_agent.readme.facts import RepositoryFacts, sha256_text
from readme_agent.registry.models import PolicyProfile

PROMPTS_DIR = Path("prompts") / "relationship_explained"


def _load_asset(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def prompt_content_hash() -> str:
    combined = _load_asset("system.txt") + "\x00" + _load_asset("user.txt")
    return sha256_text(combined)


def build_prompt(facts: RepositoryFacts, policy: PolicyProfile) -> list[dict[str, str]]:
    org_link = policy.required_elements.products_org_link
    com_link = policy.required_elements.products_com_link
    element = policy.required_elements.relationship_explained
    manifest_name = facts.manifest.get("name") or facts.manifest.get("artifact_id") or "unknown"

    system = _load_asset("system.txt").strip()
    user = (
        Template(_load_asset("user.txt"))
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
