"""Pydantic contract for categorically-stored, schema-validated LLM prompts
(GOV-024, Wave 8.5) -- mirrors capabilities/schema.py::CapabilityManifest's
shape. Lives under llm/ per prompts/README.md rule 2 ("only
src/readme_agent/llm/ may read prompts/") -- the repo-root prompts/
directory stays data-only (YAML content), this module is the schema for it.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PromptManifest(BaseModel):
    """One active, owned prompt and its exact runtime dependency boundary."""

    model_config = ConfigDict(extra="forbid")

    prompt_id: str = Field(min_length=1)
    # Not a closed Literal -- mirrors CapabilityManifest.allowed_domains's own
    # "not a closed enum, validated at build time" precedent (see
    # prompt_registry.py::_build()'s category-vs-subdirectory check), not
    # ExecutionType's closed-Literal precedent.
    category: str = Field(min_length=1)
    version: str = Field(min_length=1)
    model_route: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    runtime_consumer: str = Field(min_length=1)
    output_contract: str = Field(min_length=1)
    invalidation_scope: str = Field(min_length=1)
    dependent_artifacts: list[str] = Field(min_length=1)
    deprecated: bool = False
    replacement_prompt_id: str | None = None
    system: str
    # Optional: a job with only a turn_context_template (e.g. supervisor_turn)
    # need not also declare a separate user_template.
    user_template: str | None = None
    turn_context_template: str | None = None
    message_templates: dict[str, str] = Field(default_factory=dict)
    input_schema: dict[str, str] = Field(default_factory=dict)
    examples: list[dict] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_lifecycle(self) -> "PromptManifest":
        if self.deprecated and not self.replacement_prompt_id:
            raise ValueError("deprecated prompt requires replacement_prompt_id")
        if not self.deprecated and self.replacement_prompt_id is not None:
            raise ValueError("active prompt cannot declare replacement_prompt_id")
        return self
