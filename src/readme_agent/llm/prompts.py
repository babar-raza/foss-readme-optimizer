"""build_prompt(facts, policy) -- and *only* those two already-hashed objects.

No ambient reads, no side-channel parameters. This is the mechanical half of
the facts<->prompt coupling fix (Consistency & Determinism Tier 1 SS2):
tests/unit/test_prompt_hash_coupling.py asserts both the signature stays this
narrow and that every field expected to matter actually changes the output.
"""

from readme_agent.readme.facts import RepositoryFacts
from readme_agent.registry.models import PolicyProfile

_SYSTEM_PROMPT = (
    "You are writing a short, factual relationship-explanation paragraph for "
    "an open-source repository's README. Never invent facts, licenses, or "
    "URLs not given to you. Respond with ONLY raw JSON, no markdown fence."
)


def build_prompt(facts: RepositoryFacts, policy: PolicyProfile) -> list[dict[str, str]]:
    org_link = policy.required_elements.products_org_link
    com_link = policy.required_elements.products_com_link
    element = policy.required_elements.relationship_explained
    manifest_name = facts.manifest.get("name") or facts.manifest.get("artifact_id") or "unknown"

    user = (
        f"Repository: {facts.org_repo}\n"
        f"Manifest name: {manifest_name}\n"
        f"Detected license: {facts.detected_license or 'not detected'}\n"
        f"FOSS catalog page: {org_link.label} ({org_link.url})\n"
        f"Commercial edition page: {com_link.label} ({com_link.url})\n\n"
        f"Write relationship_paragraph ({element.min_sentences}+ sentences) explaining that "
        "this repository is the free, open-source (FOSS) edition of the corresponding "
        "commercial Aspose product, and that the commercial edition provides a broader "
        f"feature set. Cover these talking points: {', '.join(element.talking_points)}.\n\n"
        "Respond with exactly this JSON shape:\n"
        '{"relationship_paragraph": "...", "talking_points_covered": ["..."], '
        '"claims": {"license_name": "...", "commercial_link_url": "..."}}'
    )

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
