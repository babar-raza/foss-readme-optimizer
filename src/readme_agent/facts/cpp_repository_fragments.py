"""Verify inherited C++ statement fragments inside a source-bound consumer harness."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable

from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.registry.models import MinimalExamplePolicy
from readme_agent.repository_snapshot import RepositorySnapshotV1

VerifyExampleFn = Callable[[MinimalExamplePolicy], LocalProductVerificationV1 | None]

_DECLARATION = re.compile(
    r"(?m)^\s*(?:const\s+)?[A-Z][A-Za-z0-9_:<>]*(?:\s*[&*])?\s+"
    r"(?P<name>[a-z_][A-Za-z0-9_]*)\s*(?:=.*)?;\s*$"
)
_MEMBER_OWNER = re.compile(r"\b([a-z_][A-Za-z0-9_]*)\s*(?:\.|->)")
_INCOMPLETE_TYPE = re.compile(r"incomplete type ['\"]class [^'\"]*::(?P<name>[A-Z]\w*)['\"]")
_MAX_FRAGMENT_COUNT = 8
_MAX_HEADER_REPAIR_ROUNDS = 3


def _public_headers(snapshot: RepositorySnapshotV1) -> dict[str, str]:
    roots = [
        path.parent
        for path in snapshot.root_path.rglob("CMakeLists.txt")
        if (path.parent / "include").is_dir() and (path.parent / "src").is_dir()
    ]
    if not roots:
        return {}
    package_root = min(roots, key=lambda path: (len(path.parts), path.as_posix()))
    include_root = package_root / "include"
    return {
        path.stem: path.relative_to(include_root).as_posix()
        for path in include_root.rglob("*.h")
        if path.is_file()
    }


def _main_declarations(code: str) -> dict[str, str]:
    match = re.search(r"\bint\s+main\s*\([^)]*\)\s*\{(?P<body>.*)\}\s*$", code, re.DOTALL)
    body = match.group("body") if match is not None else ""
    return {item.group("name"): item.group(0).strip() for item in _DECLARATION.finditer(body)}


def _required_declarations(fragment: str, declarations: dict[str, str]) -> list[str]:
    required = set(_MEMBER_OWNER.findall(fragment)) & declarations.keys()
    changed = True
    while changed:
        changed = False
        for name in tuple(required):
            dependencies = set(_MEMBER_OWNER.findall(declarations[name])) & declarations.keys()
            if not dependencies <= required:
                required.update(dependencies)
                changed = True
    return [statement for name, statement in declarations.items() if name in required]


def _harness(
    fragments: list[MinimalExamplePolicy],
    base_example: MinimalExamplePolicy,
    headers: dict[str, str],
    extra_header_names: set[str],
) -> MinimalExamplePolicy:
    declarations = _main_declarations(base_example.code)
    fragment_text = "\n".join(item.code for item in fragments)
    header_names = {
        token for token in re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", fragment_text) if token in headers
    }
    header_names.update(extra_header_names & headers.keys())
    base_includes = {
        line.strip()
        for line in base_example.code.splitlines()
        if line.strip().startswith("#include")
    }
    inferred_includes = {f'#include "{headers[name]}"' for name in header_names}
    includes = "\n".join(sorted(base_includes | inferred_includes))
    namespaces = "\n".join(
        sorted(set(re.findall(r"(?m)^\s*using\s+namespace\s+[^;]+;", base_example.code)))
    )
    blocks = []
    for fragment in fragments:
        setup = "\n".join(_required_declarations(fragment.code, declarations))
        blocks.append("{\n" + (setup + "\n" if setup else "") + fragment.code.rstrip() + "\n}")
    code = f"{includes}\n\n{namespaces}\n\nint main() {{\n" + "\n".join(blocks)
    code += "\nreturn 0;\n}\n"
    return MinimalExamplePolicy(
        language="cpp",
        class_name="ReadmeFragmentHarness",
        code=code,
        evidence_paths=sorted(
            set(path for fragment in fragments for path in fragment.evidence_paths)
        ),
        required_symbols=sorted(header_names),
    )


def verified_cpp_readme_fragments(
    snapshot: RepositorySnapshotV1,
    candidates: Iterable[MinimalExamplePolicy],
    *,
    base_example: MinimalExamplePolicy | None,
    verify_example_fn: VerifyExampleFn,
) -> list[dict[str, object]]:
    """Return exact inherited fragments only after one isolated harness compiles."""

    if base_example is None or base_example.language != "cpp":
        return []
    fragments = [
        candidate
        for candidate in candidates
        if candidate.language == "cpp"
        and "README.md" in candidate.evidence_paths
        and "#include" not in candidate.code
        and re.search(r"\bint\s+main\s*\(", candidate.code) is None
    ][:_MAX_FRAGMENT_COUNT]
    if not fragments:
        return []
    headers = _public_headers(snapshot)
    if not headers or not _main_declarations(base_example.code):
        return []
    extra_headers: set[str] = set()
    result: LocalProductVerificationV1 | None = None
    harness: MinimalExamplePolicy | None = None
    for _ in range(_MAX_HEADER_REPAIR_ROUNDS):
        harness = _harness(fragments, base_example, headers, extra_headers)
        result = verify_example_fn(harness)
        if (
            result is not None
            and result.truth_eligible
            and result.outcome == "SOURCE_BUILD_VERIFIED"
        ):
            break
        diagnostic = result.example_compile if result is not None else None
        discovered = (
            {match.group("name") for match in _INCOMPLETE_TYPE.finditer(diagnostic.stderr)}
            if diagnostic is not None
            else set()
        )
        if not discovered - extra_headers:
            return []
        extra_headers.update(discovered)
    else:
        return []
    if result is None or harness is None or result.compiled_consumer is None:
        return []
    harness_sha256 = hashlib.sha256(harness.code.encode("utf-8")).hexdigest()
    return [
        {
            "title": f"readme_fragment_{index}",
            "language": "cpp",
            "code": fragment.code.rstrip() + "\n",
            "evidence_paths": list(fragment.evidence_paths),
            "static_api_verified": True,
            "runtime_verified": False,
            "verification_outcome": "SOURCE_BUILD_VERIFIED",
            "public_api_sha256": result.public_api_sha256,
            "contextual_harness_sha256": harness_sha256,
            "compiled_consumer_example_sha256": result.compiled_consumer.example_sha256,
        }
        for index, fragment in enumerate(fragments, start=1)
    ]


__all__ = ["verified_cpp_readme_fragments"]
