"""Bounded, secret-free local execution boundary for verified examples."""

from __future__ import annotations

import os
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.evidence.redaction import redact
from readme_agent.gitsafety.process import run_bounded

_SAFE_ENV_NAMES = {
    "CI",
    "COMSPEC",
    "LANG",
    "LC_ALL",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
}
_SECRET_NAME_RE = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|CREDENTIAL)",
    re.IGNORECASE,
)


class ExampleExecutionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    argv: list[str]
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool
    environment_names: list[str] = Field(default_factory=list)


def secret_free_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """Allowlist process essentials and reject every credential-like name."""

    source = dict(os.environ if base is None else base)
    clean = {
        name: value
        for name, value in source.items()
        if name.upper() in _SAFE_ENV_NAMES and not _SECRET_NAME_RE.search(name)
    }
    clean["CI"] = "true"
    clean["GIT_TERMINAL_PROMPT"] = "0"
    clean["GCM_INTERACTIVE"] = "never"
    return clean


def execute_example(
    argv: list[str],
    *,
    workspace: Path,
    timeout_seconds: float,
    base_environment: dict[str, str] | None = None,
) -> ExampleExecutionResultV1:
    """Execute argv without a shell, interactive input, or inherited credentials.

    This is a local secret/process boundary, not an OS sandbox. Production package
    installation still belongs in a disposable isolated Actions job.
    """

    if not argv or not argv[0]:
        raise ValueError("example argv must identify an executable")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise ValueError("example timeout must be within (0, 300] seconds")
    if not workspace.is_dir():
        raise ValueError(f"example workspace does not exist: {workspace}")

    source = dict(os.environ if base_environment is None else base_environment)
    removed_secret_values = [
        value for name, value in source.items() if _SECRET_NAME_RE.search(name) and value
    ]
    environment = secret_free_environment(source)
    result = run_bounded(
        argv,
        cwd=workspace,
        timeout=timeout_seconds,
        env=environment,
    )
    return ExampleExecutionResultV1(
        argv=argv,
        return_code=result.returncode,
        stdout=redact(result.stdout, removed_secret_values),
        stderr=redact(result.stderr, removed_secret_values),
        timed_out=result.returncode == 124,
        environment_names=sorted(environment),
    )
