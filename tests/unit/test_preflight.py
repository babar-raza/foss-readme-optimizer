from dataclasses import dataclass

from readme_agent.preflight import github_check, llm_check


@dataclass
class FakeResponse:
    status_code: int
    _json: dict
    headers: dict | None = None

    def json(self):
        return self._json


class TestGithubCheck:
    def test_check_repo_ok(self, monkeypatch):
        def fake_get(url, headers, timeout):
            return FakeResponse(200, {"default_branch": "main", "license": {"spdx_id": "MIT"}})

        monkeypatch.setattr(github_check.requests, "get", fake_get)
        result = github_check.check_repo("aspose-3d-foss/Aspose.3D-FOSS-for-Java", "tok")
        assert result.ok
        assert result.default_branch == "main"
        assert result.license == "MIT"

    def test_check_repo_null_license(self, monkeypatch):
        def fake_get(url, headers, timeout):
            return FakeResponse(200, {"default_branch": "master", "license": None})

        monkeypatch.setattr(github_check.requests, "get", fake_get)
        result = github_check.check_repo("aspose-cells-foss/Aspose.Cells-FOSS-for-Java", "tok")
        assert result.ok
        assert result.license is None

    def test_check_repo_404(self, monkeypatch):
        def fake_get(url, headers, timeout):
            return FakeResponse(404, {})

        monkeypatch.setattr(github_check.requests, "get", fake_get)
        result = github_check.check_repo("some-org/not-listed", "tok")
        assert not result.ok
        assert result.http_status == 404

    def test_check_identity_ok(self, monkeypatch):
        def fake_get(url, headers, timeout):
            return FakeResponse(
                200, {"login": "babar-raza"}, headers={"X-OAuth-Scopes": "repo, workflow"}
            )

        monkeypatch.setattr(github_check.requests, "get", fake_get)
        identity = github_check.check_identity("tok")
        assert identity.ok
        assert identity.login == "babar-raza"
        assert identity.scopes == ["repo", "workflow"]


class TestLlmCheck:
    MODELS_BODY = {
        "data": [
            {"id": "qwen3-next"},
            {"id": "experimental"},
            {"id": "gpt-oss"},
            {"id": "recommended"},
            {"id": "qwen3-embedding-8b"},
            {"id": "Qwen2.5-VL-7B"},
            {"id": "stable-diffusion-3.5-large"},
        ]
    }

    def test_candidate_filtering_excludes_embedding_vision_diffusion(self):
        candidates = [
            m["id"] for m in self.MODELS_BODY["data"] if llm_check.is_text_chat_candidate(m["id"])
        ]
        assert set(candidates) == {"qwen3-next", "experimental", "gpt-oss", "recommended"}

    def test_default_model_selected_when_live_and_unset(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)

        def fake_get(url, headers, timeout):
            return FakeResponse(200, self.MODELS_BODY)

        monkeypatch.setattr(llm_check.requests, "get", fake_get)
        result = llm_check.check_models("https://example/v1", "key")
        assert result.ok
        assert result.selected_model == "qwen3-next"

    def test_explicit_model_not_in_list_is_hard_blocked(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "not-a-real-model")

        def fake_get(url, headers, timeout):
            return FakeResponse(200, self.MODELS_BODY)

        monkeypatch.setattr(llm_check.requests, "get", fake_get)
        result = llm_check.check_models("https://example/v1", "key")
        assert not result.ok
        assert "not-a-real-model" in result.error

    def test_explicit_model_in_list_is_used_even_if_default_differs(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "qwen3-next")

        def fake_get(url, headers, timeout):
            return FakeResponse(200, self.MODELS_BODY)

        monkeypatch.setattr(llm_check.requests, "get", fake_get)
        result = llm_check.check_models("https://example/v1", "key")
        assert result.ok
        assert result.selected_model == "qwen3-next"

    def test_default_missing_and_unset_fails_closed(self, monkeypatch):
        monkeypatch.delenv("LLM_MODEL", raising=False)

        def fake_get(url, headers, timeout):
            return FakeResponse(200, {"data": [{"id": "gpt-oss"}]})

        monkeypatch.setattr(llm_check.requests, "get", fake_get)
        result = llm_check.check_models("https://example/v1", "key")
        assert not result.ok
        assert "not in the live model list" in result.error

    def test_non_200_fails(self, monkeypatch):
        def fake_get(url, headers, timeout):
            return FakeResponse(500, {})

        monkeypatch.setattr(llm_check.requests, "get", fake_get)
        result = llm_check.check_models("https://example/v1", "key")
        assert not result.ok
