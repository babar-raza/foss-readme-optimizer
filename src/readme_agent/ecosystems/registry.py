"""Dispatch by platform string. Additive: new platforms are new entries, not
new call sites. `known_manifest_globs()` is the single source of truth for
which manifest filename(s) signal each platform -- `inspection/file_inventory.py`
and this module both read it, never duplicated between them.
"""

from pathlib import Path

from readme_agent.ecosystems import cpp, dotnet, go, java, python, typescript
from readme_agent.errors import ConfigError

_PARSERS = {
    "java": java.parse,
    "python": python.parse,
    "net": dotnet.parse,
    "typescript": typescript.parse,
    "go": go.parse,
    "cpp": cpp.parse,
}

# Candidate manifest filenames/globs per platform, in priority order.
# Java and Python each have two real candidates (Maven-or-Gradle,
# pyproject.toml-or-setup.py) -- matches the proven aspose.org reference's
# own multi-file-per-platform reality, not an invented simplification.
_MANIFEST_GLOBS: dict[str, tuple[str, ...]] = {
    "java": ("pom.xml", "build.gradle"),
    "python": ("pyproject.toml", "setup.py"),
    "net": ("*.csproj",),
    "typescript": ("package.json",),
    "go": ("go.mod",),
    "cpp": ("CMakeLists.txt",),
}


def known_manifest_globs() -> dict[str, tuple[str, ...]]:
    return dict(_MANIFEST_GLOBS)


def parse_manifest(ecosystem: str, repo_root: Path) -> dict[str, str]:
    parser = _PARSERS.get(ecosystem)
    if parser is None:
        raise ConfigError(
            f"no manifest parser registered for ecosystem {ecosystem!r} (known: {sorted(_PARSERS)})"
        )
    return parser(repo_root)
