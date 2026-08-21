"""Read-only adapter for the battle-tested Aspose.org native format extractor."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from readme_agent.facts.aspose_org_dependency_snapshot import (
    snapshot_aspose_org_dependencies,
)
from readme_agent.facts.aspose_org_format_contract import (
    ASPOSE_ORG_FORMATS_RELATIVE_PATH,
    AsposeOrgFormatEvidenceV1,
    AsposeOrgFormatExtractionV1,
)
from readme_agent.facts.aspose_org_vendored_source import (
    VendoredAsposeOrgSourceV1,
    load_vendored_aspose_org_source,
)
from readme_agent.facts.dotnet_3d_format_functionality import (
    corroborate_dotnet_3d_format_directions,
)
from readme_agent.facts.dotnet_email_format_functionality import (
    corroborate_dotnet_email_format_directions,
)
from readme_agent.facts.example_execution import secret_free_environment
from readme_agent.facts.python_family_format_functionality import (
    corroborate_python_family_format_directions,
)
from readme_agent.facts.python_format_functionality import (
    corroborate_python_primary_format_directions,
)

_PLATFORM_ALIASES = {"dotnet": "net", ".net": "net", "csharp": "net", "ts": "typescript"}
_LANGUAGE_BY_PLATFORM = {
    "python": "python",
    "net": "csharp",
    "java": "java",
    "cpp": "cpp",
    "typescript": "typescript",
    "javascript": "javascript",
    "nodejs": "javascript",
    "go": "go",
    "rust": "rust",
}
_SCRIPT = r"""
import json, sys, types
from pathlib import Path
pipeline, platform, language, family, repo = sys.argv[1:]
package = types.ModuleType("extraction")
package.__package__ = "extraction"
package.__path__ = [str(Path(pipeline) / "extraction")]
sys.modules["extraction"] = package
from extraction.formats import detect_formats
from extraction.package_root import detect_package_root
from extraction.tree_helpers import get_parser
root = Path(repo)
package_root = detect_package_root(root, platform)
formats, _claims = detect_formats(get_parser(language), language, package_root, root, family)
print(json.dumps(formats, sort_keys=True))
"""


def _adapter_environment() -> dict[str, str]:
    environment = secret_free_environment()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def _source() -> VendoredAsposeOrgSourceV1:
    return load_vendored_aspose_org_source()


def extract_aspose_org_formats(
    repository_root: Path,
    *,
    platform: str,
    family: str,
    source_revision: str | None = None,
) -> AsposeOrgFormatExtractionV1:
    """Run only Aspose.org's format extractor against one immutable snapshot."""

    try:
        source = _source()
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return AsposeOrgFormatExtractionV1(
            status="unavailable", detail=f"vendored extractor is unavailable: {exc}"
        )
    root = source.root
    pipeline = source.pipeline
    extractor = pipeline / "extraction" / "formats.py"
    if not extractor.is_file():
        return AsposeOrgFormatExtractionV1(
            status="unavailable",
            extractor_revision=source.source_commit,
            detail="vendored Aspose.org extractor is unavailable",
        )
    normalized_platform = _PLATFORM_ALIASES.get(platform.casefold(), platform.casefold())
    language = _LANGUAGE_BY_PLATFORM.get(normalized_platform)
    if language is None:
        return AsposeOrgFormatExtractionV1(
            status="unavailable",
            extractor_revision=source.source_commit,
            detail=f"unsupported Aspose.org extractor platform: {normalized_platform}",
        )
    revision_before = source.source_commit
    try:
        dependency_before = snapshot_aspose_org_dependencies(root, pipeline)
    except ValueError as exc:
        return AsposeOrgFormatExtractionV1(
            status="unavailable",
            extractor_revision=revision_before,
            detail=str(exc),
        )
    extractor_sha256 = dependency_before.files[ASPOSE_ORG_FORMATS_RELATIVE_PATH]

    def provenance_result(
        *,
        status: Literal["available", "unavailable"],
        detail: str,
        formats: list[AsposeOrgFormatEvidenceV1] | None = None,
    ) -> AsposeOrgFormatExtractionV1:
        return AsposeOrgFormatExtractionV1(
            status=status,
            formats=formats or [],
            extractor_revision=revision_before,
            extractor_sha256=extractor_sha256,
            dependency_sha256=dependency_before.canonical_sha256,
            dependency_files=dependency_before.files,
            detail=detail,
        )

    result: subprocess.CompletedProcess[str] | None = None
    execution_error: str | None = None
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                _SCRIPT,
                str(pipeline),
                normalized_platform,
                language,
                family.casefold(),
                str(repository_root.resolve()),
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=_adapter_environment(),
        )
    except subprocess.TimeoutExpired:
        execution_error = "Aspose.org extractor timed out"
    try:
        dependency_after = snapshot_aspose_org_dependencies(root, pipeline)
        source_after = _source()
    except ValueError as exc:
        return provenance_result(
            status="unavailable",
            detail=f"extractor dependency changed during execution: {exc}",
        )
    if (
        revision_before != source_after.source_commit
        or source.aggregate_sha256 != source_after.aggregate_sha256
        or dependency_before != dependency_after
    ):
        return provenance_result(
            status="unavailable",
            detail="extractor revision or transitive dependency bytes changed during execution",
        )
    if execution_error is not None:
        return provenance_result(
            status="unavailable",
            detail=execution_error,
        )
    assert result is not None
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "extractor failed"
        return provenance_result(
            status="unavailable",
            detail=detail[:1000],
        )
    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, list):
            raise TypeError("extractor output must be a JSON list")
        formats = [AsposeOrgFormatEvidenceV1.model_validate(item) for item in payload]
        if normalized_platform == "python":
            formats = corroborate_python_primary_format_directions(
                repository_root,
                family=family,
                formats=formats,
            )
            formats = corroborate_python_family_format_directions(
                repository_root,
                family=family,
                source_revision=source_revision,
                formats=formats,
            )
        elif normalized_platform == "net" and family.casefold() == "3d":
            formats = corroborate_dotnet_3d_format_directions(
                repository_root,
                source_revision=source_revision or "",
                formats=formats,
            )
        elif normalized_platform == "net" and family.casefold() == "email":
            formats = corroborate_dotnet_email_format_directions(
                repository_root,
                source_revision=source_revision or "",
                formats=formats,
            )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return provenance_result(
            status="unavailable",
            detail=f"invalid extractor output: {exc}",
        )
    return provenance_result(
        status="available",
        formats=formats,
        detail=f"accepted {len(formats)} native format records",
    )
