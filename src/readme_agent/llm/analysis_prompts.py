"""The one place `capabilities/compare_against_presentation_standard.py`'s
and `capabilities/review_visual_asset_accuracy.py`'s prompt content is read
from `prompts/` (Wave 8.6) -- per `prompts/README.md` rule 2 ("only
`src/readme_agent/llm/` may read `prompts/`"), mirroring `llm/verification_
prompts.py`'s own sanctioned-reader pattern."""

import base64
from string import Template

from readme_agent.llm import prompt_registry


def build_presentation_standard_compliance_messages(
    org_repo: str, readme_text: str, presentation_standard_excerpt: str
) -> list[dict]:
    manifest = prompt_registry.get("presentation_standard_compliance")
    assert manifest is not None, "prompts/analysis/presentation_standard_compliance.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template)
        .substitute(
            org_repo=org_repo,
            readme_text=readme_text,
            presentation_standard_excerpt=presentation_standard_excerpt,
        )
        .strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]


def build_visual_asset_accuracy_messages(
    org_repo: str, product_facts_excerpt: str, image_bytes: bytes, image_media_type: str
) -> list[dict]:
    """Vision content-parts shape (OpenAI-compatible): the text portion comes
    from the registry like every other prompt; the image is attached as a
    separate content-part by this Python code, never string-substituted into
    the template itself."""
    manifest = prompt_registry.get("visual_asset_accuracy")
    assert manifest is not None, "prompts/verification/visual_asset_accuracy.yaml missing"
    assert manifest.user_template is not None
    text_content = (
        Template(manifest.user_template)
        .substitute(org_repo=org_repo, product_facts_excerpt=product_facts_excerpt)
        .strip()
    )
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    return [
        {"role": "system", "content": manifest.system.strip()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text_content},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_media_type};base64,{encoded_image}"},
                },
            ],
        },
    ]
