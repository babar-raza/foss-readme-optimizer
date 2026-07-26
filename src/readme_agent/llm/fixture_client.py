"""Fixture client: loads a canned JSON response, validated against the *same*
pydantic model a live response is validated against, so a malformed fixture
fails exactly as loudly as a malformed live response would.

`mode` is always "fixture" here, structurally -- LLMBlockResponse has no mode
field to begin with, so nothing in the fixture file itself can spoof which
mode actually produced a piece of evidence.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from readme_agent.errors import ConfigError
from readme_agent.llm.call_ledger import known_prompt_hash, record_non_provider_call
from readme_agent.llm.client import GeneratedResult
from readme_agent.llm.schema import LLMBlockResponse, LLMResponseMeta


class FixtureLLMClient:
    def __init__(
        self,
        fixture_path: Path,
        *,
        job: str = "relationship_explained",
        prompt_id: str = "relationship_explained",
    ):
        self.fixture_path = fixture_path
        self.job = job
        self.prompt_id = prompt_id

    def generate(self, messages: list[dict[str, str]]) -> GeneratedResult:
        if not self.fixture_path.exists():
            raise ConfigError(f"fixture response file not found: {self.fixture_path}")
        try:
            raw = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{self.fixture_path} is not valid JSON: {exc}") from exc
        try:
            block = LLMBlockResponse.model_validate(raw)
        except ValidationError as exc:
            raise ConfigError(
                f"{self.fixture_path} does not match LLMBlockResponse: {exc}"
            ) from exc

        meta = LLMResponseMeta(request_id=None, created=None, model="fixture")
        record_non_provider_call(
            job=self.job,
            prompt_id=self.prompt_id,
            prompt_sha256=known_prompt_hash(self.prompt_id),
            model="fixture",
            disposition="fixture",
            request=messages,
        )
        return GeneratedResult(response=block, meta=meta, mode="fixture")
