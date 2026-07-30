"""Explicit credential-provider boundary for the disposable staging runner."""

from readme_agent.capabilities import staging_effect


def test_cli_selects_github_app_without_rewriting_it_to_staging_pat(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setenv("README_AGENT_AUTHORIZATION_DIR", "pre-test")
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "pre-test")

    def execute(**kwargs):
        captured.update(kwargs)
        captured["provider"] = staging_effect.os.environ["README_AGENT_PRODUCTION_AUTH"]
        captured["authorization_env"] = staging_effect.os.environ["README_AGENT_AUTHORIZATION_DIR"]
        return {"ok": True}

    monkeypatch.setattr(staging_effect, "execute_staging_effect", execute)
    monkeypatch.setattr(staging_effect, "write_redacted_json", lambda path, payload: None)

    authorization_dir = tmp_path / "authorization"
    result = staging_effect.main(
        [
            "--source-repository",
            "source/widget",
            "--target-repository",
            "staging/widget",
            "--cohort-manifest",
            str(tmp_path / "cohort.json"),
            "--staging-manifest",
            str(tmp_path / "targets.json"),
            "--authorization-dir",
            str(authorization_dir),
            "--auth-provider",
            "github_app",
            "--output",
            str(tmp_path / "result.json"),
        ]
    )

    assert result == 0
    assert captured["provider"] == "github_app"
    assert captured["authorization_env"] == str(authorization_dir.resolve())


def test_cli_retains_explicit_act_staging_provider(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setenv("README_AGENT_AUTHORIZATION_DIR", "pre-test")
    monkeypatch.setenv("README_AGENT_PRODUCTION_AUTH", "pre-test")

    def execute(**kwargs):
        captured["provider"] = staging_effect.os.environ["README_AGENT_PRODUCTION_AUTH"]
        return {"ok": True}

    monkeypatch.setattr(staging_effect, "execute_staging_effect", execute)
    monkeypatch.setattr(staging_effect, "write_redacted_json", lambda path, payload: None)

    result = staging_effect.main(
        [
            "--source-repository",
            "source/widget",
            "--target-repository",
            "staging/widget",
            "--cohort-manifest",
            str(tmp_path / "cohort.json"),
            "--staging-manifest",
            str(tmp_path / "targets.json"),
            "--authorization-dir",
            str(tmp_path / "authorization"),
            "--auth-provider",
            "staging_pat",
            "--output",
            str(tmp_path / "result.json"),
        ]
    )

    assert result == 0
    assert captured["provider"] == "staging_pat"
