"""Live proof against the real LLM gateway -- real network, real secrets."""

import pytest

from readme_agent import env
from readme_agent.llm.live_client import LiveLLMClient

_SHAPE = (
    '{"relationship_paragraph": "<2-3 sentences>", '
    '"talking_points_covered": ["open_source_scope", "commercial_upgrade_path"], '
    '"claims": {"license_name": "MIT", '
    '"commercial_link_url": "https://products.aspose.com/3d/java/"}}'
)
_PROMPT = f"""Respond with ONLY raw JSON (no markdown fence), matching exactly this shape:
{_SHAPE}

Write relationship_paragraph explaining that Aspose.3D FOSS for Java is a free, \
open-source, MIT-licensed subset of the commercial Aspose.3D for Java product, \
and that upgrading to the commercial edition unlocks a broader feature set."""


@pytest.mark.live
def test_live_generate_matches_schema():
    client = LiveLLMClient(env.llm_base_url(), env.llm_api_key(), env.llm_model())

    result = client.generate([{"role": "user", "content": _PROMPT}])

    assert result.mode == "live"
    assert len(result.response.relationship_paragraph) > 10
    assert result.meta.model == env.llm_model()
