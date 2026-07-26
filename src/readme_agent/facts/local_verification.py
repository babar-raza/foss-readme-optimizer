"""Verify source acquisition and exact examples in disposable secret-free workspaces."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from threading import Lock

from readme_agent import env
from readme_agent.facts import java_toolchain
from readme_agent.facts.example_execution import ExampleExecutionResultV1, execute_example
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.example_verifiers import cpp as cpp_verifier
from readme_agent.facts.example_verifiers import rust as rust_verifier
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

_CACHE: dict[str, LocalProductVerificationV1] = {}
_CACHE_LOCK = Lock()
_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
)
_VERIFICATION_CONTRACT_FILES = (
    "local_verification.py",
    "example_execution.py",
    "example_quality.py",
    "repository_examples.py",
    "example_verification_schema.py",
    "example_verifiers/cpp.py",
    "example_verifiers/rust.py",
    # This gate converts compiler output into repair feedback and decides
    # whether the drafted example becomes a verified fact. A change there
    # must invalidate same-revision blocked/accepted fact evidence too.
    "../capabilities/draft_product_truth.py",
)


def local_verification_contract_hash() -> str:
    """Fingerprint every implementation file that determines example acceptance."""

    root = Path(__file__).parent
    digest = hashlib.sha256()
    for relative_path in _VERIFICATION_CONTRACT_FILES:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _cache_key(snapshot: RepositorySnapshotV1, example: MinimalExamplePolicy) -> str:
    payload = "\0".join(
        [
            snapshot.org_repo,
            snapshot.source_revision,
            snapshot.inventory_sha256,
            example.language,
            example.class_name,
            example.code,
            env.java_home() or "",
            local_verification_contract_hash(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _java_toolchain_blocked(result: ExampleExecutionResultV1) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    signals = (
        "invalid target release",
        "release version 21 not supported",
        "source option 21 is not supported",
        "target option 21 is not supported",
        "java_home",
        "mvn is not recognized",
        "javac is not recognized",
    )
    return result.return_code in {2, 9009} or any(signal in text for signal in signals)


def _missing_tool_result(tool: str) -> ExampleExecutionResultV1:
    return ExampleExecutionResultV1(
        argv=[tool],
        return_code=9009,
        stdout="",
        stderr=f"required executable is not available on PATH: {tool}",
        timed_out=False,
        environment_names=[],
    )


def _resolve_java_toolchain(
    workspace: Path,
) -> tuple[Path | None, int, str | None]:
    """Detect the JDK major version `workspace`'s own pom.xml REQUIRES
    (`java_toolchain.required_java_major_version`) and auto-provision a
    matching JDK (`java_toolchain.provision_jdk`) -- RPOC-041: replaces the
    prior behavior of trying whatever `README_AGENT_JAVA_HOME`/ambient PATH
    happened to provide and only discovering a version mismatch from
    Maven's error text after the fact. An explicit, already-matching
    `README_AGENT_JAVA_HOME` is still preferred over a download (handled
    inside `provision_jdk`); only an unrecoverable provisioning failure
    (no network, no published build, checksum mismatch, ...) returns a
    detail string instead of a path."""
    required_major = java_toolchain.required_java_major_version(workspace / "pom.xml")
    try:
        java_home = java_toolchain.provision_jdk(required_major)
    except java_toolchain.JavaToolchainError as exc:
        return None, required_major, f"required JDK {required_major} unavailable: {exc}"
    return java_home, required_major, None


def _verify_java(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    maven = shutil.which("mvn")
    if maven is None:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="java",
            outcome="BLOCKED_TOOLCHAIN",
            detail="required executable is unavailable: mvn",
            build=_missing_tool_result("mvn"),
        )

    java_home, required_major, provisioning_failure = _resolve_java_toolchain(workspace)
    if java_home is None:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="java",
            outcome="BLOCKED_TOOLCHAIN",
            detail=provisioning_failure or f"required JDK {required_major} unavailable",
            build=_missing_tool_result("javac"),
        )
    javac_name = "javac.exe" if os.name == "nt" else "javac"
    javac_path = java_home / "bin" / javac_name
    if not javac_path.is_file():
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="java",
            outcome="BLOCKED_TOOLCHAIN",
            detail=f"provisioned JDK {required_major} at {java_home} is missing javac",
            build=_missing_tool_result("javac"),
        )
    javac = str(javac_path)
    process_environment = dict(os.environ)
    process_environment["JAVA_HOME"] = str(java_home)
    process_environment["PATH"] = f"{java_home / 'bin'}{os.pathsep}{process_environment['PATH']}"
    build = execute_example(
        [maven, "-q", "-DskipTests", "package"],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=process_environment,
    )
    if build.return_code != 0:
        blocked = _java_toolchain_blocked(build)
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="java",
            outcome="BLOCKED_TOOLCHAIN" if blocked else "BUILD_FAILED",
            detail=(
                "required Java/Maven toolchain is unavailable or incompatible"
                if blocked
                else "source build failed"
            ),
            build=build,
        )

    example_path = workspace / f"{example.class_name}.java"
    example_path.write_text(example.code, encoding="utf-8", newline="\n")
    output_path = workspace / "target" / "readme-agent-example"
    output_path.mkdir(parents=True, exist_ok=True)
    compile_result = execute_example(
        [
            javac,
            "-cp",
            str(workspace / "target" / "classes"),
            "-d",
            str(output_path),
            str(example_path),
        ],
        workspace=workspace,
        timeout_seconds=120,
        base_environment=process_environment,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="java",
        outcome=(
            "SOURCE_BUILD_VERIFIED"
            if compile_result.return_code == 0
            else "BLOCKED_TOOLCHAIN"
            if _java_toolchain_blocked(compile_result)
            else "BUILD_FAILED"
        ),
        detail=(
            "source build and exact README example compilation passed"
            if compile_result.return_code == 0
            else "exact README example compilation failed"
        ),
        build=build,
        example_compile=compile_result,
    )


def _resolve_python_executable() -> str | None:
    return shutil.which("python") or shutil.which("python3")


# --------------------------------------------------------------------------
# RPOC-035: dotnet/python/typescript/go verifiers.
#
# Each follows `_verify_java`'s exact two-phase shape (build the real repo,
# then compile the exact README example against it) and outcome vocabulary
# (`SOURCE_BUILD_VERIFIED`/`BLOCKED_TOOLCHAIN`/`BUILD_FAILED`), but -- unlike
# `_verify_java` -- none of these auto-provisions a missing toolchain the way
# `java_toolchain.py` downloads a matching JDK. That is a deliberately larger
# scope this taskcard does not take on; checking for an already-installed
# toolchain on PATH and returning `BLOCKED_TOOLCHAIN` with a clear message
# when it is missing is the honestly-scoped behavior here. Every phase is
# compile-only (never executes the example), matching `_verify_java`'s own
# `javac`-only second phase -- actually running an example would need its
# real published package installed (`pip install`/`npm install`/a NuGet
# package restore beyond the repo's own project), which needs network access
# this local, disposable, secret-free boundary deliberately does not grant
# (see this module's `execute_example` docstring).
# --------------------------------------------------------------------------


_DEFAULT_DOTNET_TARGET_FRAMEWORK = "net8.0"
# Newest LTS at the time this was written -- like `java_toolchain.
# DEFAULT_JAVA_MAJOR_VERSION`, no onboarded .NET repo exists yet to learn a
# real default from; update this once one does.
_DEFAULT_GO_VERSION = "1.21"
# Matches `DEFAULT_JAVA_MAJOR_VERSION`'s reasoning: no onboarded Go repo yet.

_EXAMPLE_TSCONFIG = (
    "{\n"
    '  "compilerOptions": {\n'
    '    "target": "ES2020",\n'
    '    "module": "commonjs",\n'
    '    "strict": false,\n'
    '    "skipLibCheck": true,\n'
    '    "noEmit": true\n'
    "  }\n"
    "}\n"
)


def _dotnet_hermetic_environment(workspace: Path) -> dict[str, str]:
    """Disposable, run-scoped profile for `dotnet build` -- RPOC-035.

    Empirically required (bisected live against a real `dotnet build`, not
    assumed): NuGet's own settings resolution throws `ArgumentNullException`
    under this project's tiny cross-ecosystem allowlist, needing a handful of
    ordinary Windows system-context facts to even start (added to
    `example_execution._SAFE_ENV_NAMES`, see that module's own comment for
    the full story). The profile-shaped variables that *could* otherwise leak
    ambient state (a real `NuGet.Config`/dotfile under the real user profile)
    are always pointed at a disposable directory scoped to this one
    verification run here -- never the ambient real profile -- mirroring
    `_verify_java`'s own `JAVA_HOME` override.
    """
    profile_root = workspace.parent / "dotnet-profile"
    profile_root.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ)
    environment["HOME"] = str(profile_root)
    environment["APPDATA"] = str(profile_root / "roaming")
    environment["LOCALAPPDATA"] = str(profile_root / "local")
    environment["NUGET_PACKAGES"] = str(profile_root / "nuget-packages")
    environment["DOTNET_CLI_HOME"] = str(profile_root)
    environment["DOTNET_NOLOGO"] = "1"
    environment["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    environment["DOTNET_SKIP_FIRST_TIME_EXPERIENCE"] = "1"
    if os.name == "nt":
        drive, tail = os.path.splitdrive(str(profile_root))
        environment["USERPROFILE"] = str(profile_root)
        environment["HOMEDRIVE"] = drive
        environment["HOMEPATH"] = tail
    return environment


def _discover_csproj(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> Path | None:
    """Select the profiled .NET project that owns the example evidence.

    RepositorySnapshotV1 already records every package root, so a multi-project
    repository must not be treated as if a project file necessarily lives at
    its root. Evidence-path ownership is the strongest deterministic selector;
    a production/library root is the bounded fallback when the example cites
    only repository-wide documentation.
    """

    candidates: list[tuple[str, Path]] = []
    for package_root in snapshot.package_roots:
        if package_root.ecosystem not in {"net", "dotnet"}:
            continue
        relative = Path(package_root.manifest_path)
        candidate = (workspace / relative).resolve()
        try:
            candidate.relative_to(workspace.resolve())
        except ValueError:
            continue
        if candidate.is_file() and candidate.suffix.lower() == ".csproj":
            candidates.append((relative.as_posix().lower(), candidate))

    if not candidates:
        candidates = [
            (candidate.relative_to(workspace).as_posix().lower(), candidate)
            for candidate in sorted(workspace.glob("*.csproj"))
        ]
    if not candidates:
        return None

    evidence_paths = [Path(path).as_posix().lower() for path in example.evidence_paths]

    def selection_key(item: tuple[str, Path]) -> tuple[int, int, int, str]:
        manifest_path, _ = item
        package_path = Path(manifest_path).parent.as_posix().rstrip(".").rstrip("/")
        owns_evidence = any(
            evidence_path == package_path or evidence_path.startswith(f"{package_path}/")
            for evidence_path in evidence_paths
            if package_path
        )
        path_parts = set(Path(manifest_path).parts)
        is_test_or_sample = bool(path_parts & {"test", "tests", "sample", "samples", "converter"})
        is_main = "/main/" in f"/{manifest_path}/"
        return (not owns_evidence, is_test_or_sample, not is_main, manifest_path)

    return min(candidates, key=selection_key)[1]


def _dotnet_target_framework(csproj_path: Path | None) -> str:
    if csproj_path is None or not csproj_path.is_file():
        return _DEFAULT_DOTNET_TARGET_FRAMEWORK
    try:
        root = ET.parse(csproj_path).getroot()
    except ET.ParseError:
        return _DEFAULT_DOTNET_TARGET_FRAMEWORK
    for tag in ("TargetFramework", "TargetFrameworks"):
        for elem in root.iter():
            if elem.tag == tag and elem.text and elem.text.strip():
                return elem.text.strip().split(";")[0]
    return _DEFAULT_DOTNET_TARGET_FRAMEWORK


def _dotnet_toolchain_blocked(result: ExampleExecutionResultV1) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    signals = (
        "dotnet is not recognized",
        "dotnet: command not found",
        "no .net sdks were found",
        "it was not possible to find any installed .net core sdks",
        "you must install or update .net to run this application",
        "requires .net sdk version",
        "framework 'microsoft.netcore.app', version",
    )
    return result.return_code in {9009, 127} or any(signal in text for signal in signals)


def _verify_dotnet(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="dotnet",
            outcome="BLOCKED_TOOLCHAIN",
            detail="required executable is unavailable: dotnet",
            build=_missing_tool_result("dotnet"),
        )

    repo_csproj = _discover_csproj(snapshot, example, workspace)
    process_environment = _dotnet_hermetic_environment(workspace)
    build_argv = (
        [dotnet, "build", str(repo_csproj), "--nologo"]
        if repo_csproj is not None
        else [dotnet, "build", "--nologo"]
    )
    build = execute_example(
        build_argv,
        workspace=workspace,
        timeout_seconds=300,
        base_environment=process_environment,
    )
    if build.return_code != 0:
        blocked = _dotnet_toolchain_blocked(build)
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="dotnet",
            outcome="BLOCKED_TOOLCHAIN" if blocked else "BUILD_FAILED",
            detail=(
                "required .NET SDK toolchain is unavailable or incompatible"
                if blocked
                else "source build failed"
            ),
            build=build,
        )

    # Scaffold a disposable console project for the exact README example as
    # a sibling of `workspace` (never inside it -- the repo may already own
    # a `.csproj` at its root, and a second one there would collide) --
    # `_verify_java`'s own scaffold analog is `workspace/target/readme-agent-
    # example`, kept inside the repo copy only because Java needs no second
    # manifest file to add a compilation unit next to existing sources.
    target_framework = _dotnet_target_framework(repo_csproj)
    project_reference = (
        f'  <ItemGroup>\n    <ProjectReference Include="{repo_csproj}" />\n  </ItemGroup>\n'
        if repo_csproj is not None
        else ""
    )
    example_dir = workspace.parent / "dotnet-example"
    example_dir.mkdir(parents=True, exist_ok=True)
    (example_dir / "ReadmeAgentExample.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        "  <PropertyGroup>\n"
        "    <OutputType>Exe</OutputType>\n"
        f"    <TargetFramework>{target_framework}</TargetFramework>\n"
        "    <ImplicitUsings>enable</ImplicitUsings>\n"
        "    <Nullable>enable</Nullable>\n"
        "  </PropertyGroup>\n"
        f"{project_reference}"
        "</Project>\n",
        encoding="utf-8",
        newline="\n",
    )
    (example_dir / f"{example.class_name}.cs").write_text(
        example.code, encoding="utf-8", newline="\n"
    )
    compile_result = execute_example(
        [dotnet, "build", "--nologo"],
        workspace=example_dir,
        timeout_seconds=120,
        base_environment=process_environment,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="dotnet",
        outcome=(
            "SOURCE_BUILD_VERIFIED"
            if compile_result.return_code == 0
            else "BLOCKED_TOOLCHAIN"
            if _dotnet_toolchain_blocked(compile_result)
            else "BUILD_FAILED"
        ),
        detail=(
            "source build and exact README example compilation passed"
            if compile_result.return_code == 0
            else "exact README example compilation failed"
        ),
        build=build,
        example_compile=compile_result,
    )


def _python_toolchain_blocked(result: ExampleExecutionResultV1) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    signals = ("python is not recognized", "python: command not found")
    return result.return_code in {9009, 127} or any(signal in text for signal in signals)


def _verify_python(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    """`python -m py_compile`, Python's direct syntax/bytecode-compile analog
    to `javac`'s compile-only step -- never `pip install`/execute the
    example, which would need the real published package (network). No
    interpreter-version auto-provisioning (unlike `java_toolchain.py`):
    whatever `python`/`python3` is already on PATH is used as-is. A
    `.python-version`/`pyproject.toml` `requires-python` pin is not enforced
    here -- this taskcard's scope explicitly excludes building a second
    provisioning pipeline; that field is simple enough to defer until a real
    Python repo's policy needs it."""
    python = _resolve_python_executable()
    if python is None:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="python",
            outcome="BLOCKED_TOOLCHAIN",
            detail="required executable is unavailable: python",
            build=_missing_tool_result("python"),
        )

    build = execute_example(
        [python, "-m", "compileall", "-q", "."],
        workspace=workspace,
        timeout_seconds=300,
    )
    if build.return_code != 0:
        blocked = _python_toolchain_blocked(build)
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="python",
            outcome="BLOCKED_TOOLCHAIN" if blocked else "BUILD_FAILED",
            detail=(
                "required Python toolchain is unavailable" if blocked else "source build failed"
            ),
            build=build,
        )

    example_dir = workspace.parent / "python-example"
    example_dir.mkdir(parents=True, exist_ok=True)
    example_path = example_dir / f"{example.class_name}.py"
    example_path.write_text(example.code, encoding="utf-8", newline="\n")
    compile_result = execute_example(
        [python, "-m", "py_compile", str(example_path)],
        workspace=example_dir,
        timeout_seconds=60,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="python",
        outcome=(
            "SOURCE_BUILD_VERIFIED"
            if compile_result.return_code == 0
            else "BLOCKED_TOOLCHAIN"
            if _python_toolchain_blocked(compile_result)
            else "BUILD_FAILED"
        ),
        detail=(
            "source build and exact README example compilation passed"
            if compile_result.return_code == 0
            else "exact README example compilation failed"
        ),
        build=build,
        example_compile=compile_result,
    )


def _typescript_toolchain_blocked(result: ExampleExecutionResultV1) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    signals = (
        "tsc is not recognized",
        "tsc: command not found",
        "node is not recognized",
        "node: command not found",
        "cannot find module 'typescript'",
    )
    return result.return_code in {9009, 127} or any(signal in text for signal in signals)


def _verify_typescript(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    """`tsc --noEmit`: type-checks only, never emits or executes -- the same
    compile-only contract every verifier in this file follows. Chosen over
    `ts-node`/`npx tsx` deliberately: those execute the example, which needs
    its real imports resolved via `npm install` (network) -- the same
    limitation already documented for `_verify_python`'s `pip install`
    boundary. Requires `tsc` already resolvable on PATH; no `npm install
    typescript` fallback, since that would silently reintroduce the same
    network dependency this boundary exists to avoid."""
    node = shutil.which("node")
    tsc = shutil.which("tsc")
    if node is None or tsc is None:
        missing = "node" if node is None else "tsc"
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="typescript",
            outcome="BLOCKED_TOOLCHAIN",
            detail=f"required executable is unavailable: {missing}",
            build=_missing_tool_result(missing),
        )

    build = execute_example(
        [tsc, "--noEmit", "-p", str(workspace)],
        workspace=workspace,
        timeout_seconds=300,
    )
    if build.return_code != 0:
        blocked = _typescript_toolchain_blocked(build)
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="typescript",
            outcome="BLOCKED_TOOLCHAIN" if blocked else "BUILD_FAILED",
            detail=(
                "required Node/TypeScript toolchain is unavailable"
                if blocked
                else "source build failed"
            ),
            build=build,
        )

    example_dir = workspace.parent / "typescript-example"
    example_dir.mkdir(parents=True, exist_ok=True)
    (example_dir / "tsconfig.json").write_text(_EXAMPLE_TSCONFIG, encoding="utf-8", newline="\n")
    (example_dir / f"{example.class_name}.ts").write_text(
        example.code, encoding="utf-8", newline="\n"
    )
    compile_result = execute_example(
        [tsc, "--noEmit", "-p", str(example_dir)],
        workspace=example_dir,
        timeout_seconds=120,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="typescript",
        outcome=(
            "SOURCE_BUILD_VERIFIED"
            if compile_result.return_code == 0
            else "BLOCKED_TOOLCHAIN"
            if _typescript_toolchain_blocked(compile_result)
            else "BUILD_FAILED"
        ),
        detail=(
            "source build and exact README example compilation passed"
            if compile_result.return_code == 0
            else "exact README example compilation failed"
        ),
        build=build,
        example_compile=compile_result,
    )


def _go_hermetic_environment(workspace: Path) -> dict[str, str]:
    """Disposable `GOCACHE`/`GOPATH`/`GOMODCACHE` -- empirically required
    (not assumed): a bare `go build` under this project's tiny allowlist
    fails outright ("GOCACHE is not defined and %LocalAppData% is not
    defined") since Go refuses to run without a writable build cache.
    Scoped to this one verification run's own temp directory, never the
    ambient `~/go` -- mirrors `_verify_java`'s `JAVA_HOME` override."""
    cache_root = workspace.parent / "go-cache"
    environment = dict(os.environ)
    environment["GOCACHE"] = str(cache_root / "build")
    environment["GOPATH"] = str(cache_root / "path")
    environment["GOMODCACHE"] = str(cache_root / "path" / "pkg" / "mod")
    return environment


def _required_go_version(go_mod_path: Path) -> str:
    if not go_mod_path.is_file():
        return _DEFAULT_GO_VERSION
    try:
        text = go_mod_path.read_text(encoding="utf-8")
    except OSError:
        return _DEFAULT_GO_VERSION
    match = re.search(r"(?m)^go\s+(\d+\.\d+(?:\.\d+)?)", text)
    return match.group(1) if match else _DEFAULT_GO_VERSION


def _go_toolchain_blocked(result: ExampleExecutionResultV1) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    signals = (
        "go is not recognized",
        "go: command not found",
        "requires go >=",
        "note: module requires go",
        "go.mod requires go",
        "gocache is not defined",
    )
    return result.return_code in {9009, 127} or any(signal in text for signal in signals)


def _verify_go(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    workspace: Path,
) -> LocalProductVerificationV1:
    """`go build`, compile-only in effect: Go has no separate typecheck-vs-
    link step, but the exact-example phase never executes the built binary,
    matching this file's compile-only contract. The example module is
    deliberately self-contained (its own `go.mod`, no `replace` directive
    back to the repo's real module) rather than cross-referencing the repo's
    build output the way `_verify_dotnet`'s `ProjectReference` does: doing
    that correctly needs the repo's real module path, and no Go repo is
    onboarded yet to validate that inference against -- simpler and honestly
    scoped until one is."""
    go = shutil.which("go")
    if go is None:
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="go",
            outcome="BLOCKED_TOOLCHAIN",
            detail="required executable is unavailable: go",
            build=_missing_tool_result("go"),
        )

    process_environment = _go_hermetic_environment(workspace)
    build = execute_example(
        [go, "build", "./..."],
        workspace=workspace,
        timeout_seconds=300,
        base_environment=process_environment,
    )
    if build.return_code != 0:
        blocked = _go_toolchain_blocked(build)
        return LocalProductVerificationV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            ecosystem="go",
            outcome="BLOCKED_TOOLCHAIN" if blocked else "BUILD_FAILED",
            detail=(
                "required Go toolchain is unavailable or incompatible"
                if blocked
                else "source build failed"
            ),
            build=build,
        )

    example_dir = workspace.parent / "go-example"
    example_dir.mkdir(parents=True, exist_ok=True)
    go_version = _required_go_version(workspace / "go.mod")
    (example_dir / "go.mod").write_text(
        f"module readme-agent-example\n\ngo {go_version}\n", encoding="utf-8", newline="\n"
    )
    (example_dir / f"{example.class_name}.go").write_text(
        example.code, encoding="utf-8", newline="\n"
    )
    compile_result = execute_example(
        [go, "build", "./..."],
        workspace=example_dir,
        timeout_seconds=120,
        base_environment=process_environment,
    )
    return LocalProductVerificationV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        ecosystem="go",
        outcome=(
            "SOURCE_BUILD_VERIFIED"
            if compile_result.return_code == 0
            else "BLOCKED_TOOLCHAIN"
            if _go_toolchain_blocked(compile_result)
            else "BUILD_FAILED"
        ),
        detail=(
            "source build and exact README example compilation passed"
            if compile_result.return_code == 0
            else "exact README example compilation failed"
        ),
        build=build,
        example_compile=compile_result,
    )


_VERIFIERS = {
    "java": _verify_java,
    "dotnet": _verify_dotnet,
    "python": _verify_python,
    "typescript": _verify_typescript,
    "go": _verify_go,
    "cpp": cpp_verifier.verify,
    "rust": rust_verifier.verify,
}


def verify_local_product_example(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
) -> LocalProductVerificationV1:
    """Build a disposable copy and compile the policy's exact example."""

    verify_repository_snapshot(snapshot)
    verifier = _VERIFIERS.get(example.language)
    if verifier is None:
        raise ValueError(f"no local example verifier registered for {example.language!r}")
    key = _cache_key(snapshot, example)
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
    if cached is not None:
        return cached

    with tempfile.TemporaryDirectory(prefix="readme-agent-product-verification-") as temp:
        workspace = Path(temp) / "repository"
        shutil.copytree(snapshot.root_path, workspace, ignore=_COPY_IGNORE)
        result = verifier(snapshot, example, workspace)
    verify_repository_snapshot(snapshot)
    with _CACHE_LOCK:
        _CACHE[key] = result
    return result
