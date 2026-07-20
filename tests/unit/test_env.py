"""LLM_MODEL env override > per-job routing table > DEFAULT_LLM_MODEL (`LLM-016`)."""

from readme_agent import env


class TestLlmModelForJob:
    def test_known_job_resolves_to_its_routed_model(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert env.llm_model_for_job("relationship_explained") == "qwen3-next"

    def test_unknown_job_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)
        assert env.llm_model_for_job("some_future_job") == env.DEFAULT_LLM_MODEL

    def test_llm_model_env_override_wins_over_routing_table(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gpt-oss")
        assert env.llm_model_for_job("relationship_explained") == "gpt-oss"

    def test_relationship_explained_is_not_routed_to_gpt_oss(self):
        # LLM-016: gpt-oss scored 1/10 on freeform-JSON validity for exactly
        # this job's shape -- the routing table must never regress to it.
        assert env.JOB_MODEL_ROUTING["relationship_explained"] != "gpt-oss"
