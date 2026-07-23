"""Examples run without inherited credentials, shell expansion, or unredacted output."""

import sys

from readme_agent.facts.example_execution import execute_example, secret_free_environment


def test_secret_free_environment_drops_every_credential_like_name():
    environment = secret_free_environment(
        {
            "PATH": "safe-path",
            "GH_TOKEN": "ghp_syntheticSecretValue123456",
            "LLM_API_KEY": "sk-syntheticSecretValue123456",
            "GH_APP_PRIVATE_KEY": "private",
            "CUSTOM_PASSWORD": "password",
        }
    )

    assert environment["PATH"] == "safe-path"
    assert environment["CI"] == "true"
    assert "GH_TOKEN" not in environment
    assert "LLM_API_KEY" not in environment
    assert "GH_APP_PRIVATE_KEY" not in environment
    assert "CUSTOM_PASSWORD" not in environment


def test_execution_does_not_inherit_token_and_redacts_literal_output(tmp_path):
    fake_secret = "ghp_syntheticSecretValue123456"
    code = f"import os;print(os.getenv('GH_TOKEN'));print({fake_secret!r})"

    result = execute_example(
        [sys.executable, "-c", code],
        workspace=tmp_path,
        timeout_seconds=10,
        base_environment={"PATH": "", "GH_TOKEN": fake_secret},
    )

    assert result.return_code == 0
    assert result.stdout.splitlines()[0] == "None"
    assert fake_secret not in result.stdout
    assert "[REDACTED]" in result.stdout
    assert "GH_TOKEN" not in result.environment_names


def test_timeout_is_bounded(tmp_path):
    result = execute_example(
        [sys.executable, "-c", "while True: pass"],
        workspace=tmp_path,
        timeout_seconds=0.1,
        base_environment={},
    )

    assert result.return_code == 124
    assert result.timed_out is True
