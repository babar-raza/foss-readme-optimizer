"""The one place `verification/prose_quality.py`'s prompt content is read
from `prompts/` (Wave 8.6, `VER-006` reversal) -- per `prompts/README.md`
rule 2 ("only `src/readme_agent/llm/` may read `prompts/`"), mirroring how
`llm/prompts.py`/`supervisor/dossier.py` are the sanctioned readers for
their own jobs. `verification/prose_quality.py` never reads `prompts/`
itself; it only calls `build_prose_quality_messages()` below.

`PROSE_QUALITY_TOOL_SCHEMA` is a parameter schema, not prompt content --
mirrors `capabilities/schema.py::CapabilityManifest.to_tool_schema()`'s own
code-not-content treatment, so it stays here as a plain dict rather than
becoming YAML content."""

from string import Template

from readme_agent.llm import prompt_registry

PROSE_QUALITY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "report_prose_quality_finding",
        "description": (
            "Report whether the given paragraph reads as generic, repetitive, or "
            "mechanically-inserted prose rather than genuine, specific writing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "flagged": {"type": "boolean"},
                "quoted_span": {
                    "type": "string",
                    "description": (
                        "A verbatim substring of the reviewed paragraph that supports the "
                        "finding. Must be empty if flagged is false."
                    ),
                },
                "reason": {"type": "string"},
            },
            "required": ["flagged", "reason"],
        },
    },
}


def build_prose_quality_messages(paragraph_text: str) -> list[dict]:
    manifest = prompt_registry.get("prose_quality_check")
    assert manifest is not None, "prompts/verification/prose_quality_check.yaml missing"
    assert manifest.user_template is not None
    user_content = (
        Template(manifest.user_template).substitute(paragraph_text=paragraph_text).strip()
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user_content},
    ]
