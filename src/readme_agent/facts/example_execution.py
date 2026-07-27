"""Bounded, secret-free local execution boundary for verified examples."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.evidence.redaction import redact
from readme_agent.gitsafety.process import run_bounded

_SAFE_ENV_NAMES = {
    "CI",
    "COMSPEC",
    "JAVA_HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
    # RPOC-035 (dotnet/go verifiers, `local_verification.py`): empirically
    # confirmed (not assumed -- bisected live against a real `dotnet build`
    # and a real `go build` on a real Windows machine) that the tiny
    # allowlist above is insufficient for either toolchain to run at all,
    # not merely insecure without them:
    #   * `dotnet build` throws inside NuGet's own settings resolution
    #     (`NuGet.Common.NuGetEnvironment.GetFolderPath`) without a handful
    #     of ordinary Windows system-context facts (`ProgramFiles`,
    #     `ProgramData`, `PROCESSOR_ARCHITECTURE`, `USERNAME`, ...) --
    #     none of these is credential-bearing (directory paths, hostnames,
    #     processor facts, not secrets), and the profile-shaped ones
    #     (`USERPROFILE`/`APPDATA`/`LOCALAPPDATA`/`HOMEDRIVE`/`HOMEPATH`/
    #     `HOME`/`NUGET_PACKAGES`/`DOTNET_CLI_HOME`) are ALWAYS overridden
    #     by the caller to a disposable, run-scoped directory before
    #     reaching this allowlist (mirroring this file's own `JAVA_HOME`
    #     precedent) -- never the ambient real profile, so no ambient
    #     `NuGet.Config`/dotfile credential can be discovered through them.
    #   * `go build` refuses to run at all without a writable `GOCACHE`
    #     ("GOCACHE is not defined and %LocalAppData% is not defined");
    #     `GOPATH`/`GOMODCACHE` are included for the same disposable-
    #     override treatment.
    # `_SECRET_NAME_RE` below still strips any of these (or any future
    # addition) whose live value looks like a secret, regardless of
    # allowlist membership -- this widening does not disable that backstop.
    "APPDATA",
    "CARGO_HOME",
    "CARGO_TERM_COLOR",
    "COMPUTERNAME",
    "DOTNET_CLI_HOME",
    "DOTNET_CLI_TELEMETRY_OPTOUT",
    "DOTNET_NOLOGO",
    "DOTNET_SKIP_FIRST_TIME_EXPERIENCE",
    "GOCACHE",
    "GOMODCACHE",
    "GOPATH",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NUGET_PACKAGES",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "RUSTUP_HOME",
    "USERDOMAIN",
    "USERNAME",
    "USERPROFILE",
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
    isolation_kind: Literal[
        "host_secret_filtered",
        "isolated_result_projection",
    ] = "host_secret_filtered"
    truth_eligible: Literal[False] = False


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

    This is a local secret/process boundary, not an OS sandbox. Its typed result
    is permanently ineligible for product-truth promotion.
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
