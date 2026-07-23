"""Per-job routing table (`JOB_MODEL_ROUTING`) > `DEFAULT_LLM_MODEL` (`LLM-016`).

Wave 13.4 (`LLM-020`): `LLM_MODEL` no longer overrides a routed job by
default -- it only applies alongside the explicit
`READMEAGENT_DEBUG_MODEL_OVERRIDE=1` opt-in flag."""

from readme_agent import env


class TestLlmModelForJob:
    def test_known_job_resolves_to_its_routed_model(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert env.llm_model_for_job("relationship_explained") == "qwen3-next"

    def test_unknown_job_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert env.llm_model_for_job("some_future_job") == env.DEFAULT_LLM_MODEL

    def test_llm_model_env_alone_no_longer_overrides_the_routing_table(self, monkeypatch):
        """Wave 13.4 (`LLM-020`): the confirmed prior behavior -- a bare
        `LLM_MODEL` env var, with no debug flag, must never silently
        substitute a different model for a routed job."""
        monkeypatch.delenv("READMEAGENT_DEBUG_MODEL_OVERRIDE", raising=False)
        monkeypatch.setenv("LLM_MODEL", "gpt-oss")
        assert env.llm_model_for_job("relationship_explained") == "qwen3-next"

    def test_llm_model_override_applies_only_with_the_debug_flag_set(self, monkeypatch):
        monkeypatch.setenv("READMEAGENT_DEBUG_MODEL_OVERRIDE", "1")
        monkeypatch.setenv("LLM_MODEL", "gpt-oss")
        assert env.llm_model_for_job("relationship_explained") == "gpt-oss"

    def test_debug_flag_alone_without_llm_model_set_does_not_change_the_route(self, monkeypatch):
        monkeypatch.setenv("READMEAGENT_DEBUG_MODEL_OVERRIDE", "1")
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert env.llm_model_for_job("relationship_explained") == "qwen3-next"

    def test_debug_flag_set_to_a_non_one_value_does_not_enable_the_override(self, monkeypatch):
        monkeypatch.setenv("READMEAGENT_DEBUG_MODEL_OVERRIDE", "true")
        monkeypatch.setenv("LLM_MODEL", "gpt-oss")
        assert env.llm_model_for_job("relationship_explained") == "qwen3-next"

    def test_relationship_explained_is_not_routed_to_gpt_oss(self):
        # LLM-016: gpt-oss scored 1/10 on freeform-JSON validity for exactly
        # this job's shape -- the routing table must never regress to it.
        assert env.JOB_MODEL_ROUTING["relationship_explained"] != "gpt-oss"
