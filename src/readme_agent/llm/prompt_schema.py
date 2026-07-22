"""Pydantic contract for categorically-stored, schema-validated LLM prompts
(GOV-024, Wave 8.5) -- mirrors capabilities/schema.py::CapabilityManifest's
shape. Lives under llm/ per prompts/README.md rule 2 ("only
src/readme_agent/llm/ may read prompts/") -- the repo-root prompts/
directory stays data-only (YAML content), this module is the schema for it.
"""

from pydantic import BaseModel, Field


class PromptManifest(BaseModel):
    prompt_id: str
    # Not a closed Literal -- mirrors CapabilityManifest.allowed_domains's own
    # "not a closed enum, validated at build time" precedent (see
    # prompt_registry.py::_build()'s category-vs-subdirectory check), not
    # ExecutionType's closed-Literal precedent.
    category: str
    version: str
    # Informational only -- the real model routing stays in env.py's
    # JOB_MODEL_ROUTING; this just records which job a prompt is used for.
    model_route: str
    system: str
    # Optional: a job with only a turn_context_template (e.g. supervisor_turn)
    # need not also declare a separate user_template.
    user_template: str | None = None
    turn_context_template: str | None = None
    input_schema: dict[str, str] = Field(default_factory=dict)
    examples: list[dict] = Field(default_factory=list)
    notes: str | None = None
