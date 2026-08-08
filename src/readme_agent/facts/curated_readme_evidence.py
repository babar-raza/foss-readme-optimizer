"""Register repository-bound detail collectors for curated README retention."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from readme_agent.facts.curated_python_dependencies import (
    python_capability_dependencies,
    python_distribution_evidence,
)
from readme_agent.facts.curated_python_evidence import (
    example_inventory,
    python_optional_extras,
    python_public_surface,
    python_source_format_directions,
)
from readme_agent.facts.curated_python_implementation import python_implementation_components
from readme_agent.facts.curated_python_import_shadowing import python_import_shadowing
from readme_agent.facts.curated_repository_assets import (
    development_assets,
    repository_ci,
    third_party_notices,
)
from readme_agent.facts.curated_repository_guidance import (
    repository_contribution_guidance,
    repository_development_commands,
    repository_documentation_assets,
    repository_security_guidance,
    source_guidance_limitations,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_CollectorResult = tuple[object, list[str]]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _class_methods(path: Path, class_name: str) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()
    definition = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name),
        None,
    )
    if definition is None:
        return set()
    return {
        node.name
        for node in definition.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


_PDF_CAPABILITY_SPECS = (
    (
        "Create, load, save, merge, and inspect PDF documents",
        "src/aspose_pdf/document.py",
        "Document",
        ("load_from", "save", "merge", "validate"),
    ),
    (
        "Add and edit text and images, including text replacement and redaction",
        "src/aspose_pdf/pages.py",
        "Page",
        ("add_text", "add_image", "replace_text", "redact_text"),
    ),
    (
        "Extract text, images, and attachments",
        "src/aspose_pdf/facades.py",
        "PdfExtractor",
        ("extract_text", "get_text", "extract_image", "extract_attachment"),
    ),
    (
        "Concatenate, extract, insert, delete, and append PDF pages",
        "src/aspose_pdf/facades.py",
        "PdfFileEditor",
        ("concatenate", "extract", "insert", "delete", "append"),
    ),
    (
        "Render PDF pages to PNG or TIFF images",
        "src/aspose_pdf/pages.py",
        "Page",
        ("render", "save_as_image"),
    ),
    (
        "Create and manage interactive form fields",
        "src/aspose_pdf/forms.py",
        "Form",
        ("add_text_field", "add_checkbox", "add_radio_group", "flatten"),
    ),
    (
        "Add, update, and remove PDF annotations",
        "src/aspose_pdf/annotations/__init__.py",
        "AnnotationCollection",
        ("add", "insert", "delete", "clear"),
    ),
    (
        "Encrypt, decrypt, optimize, and compress PDF documents",
        "src/aspose_pdf/document.py",
        "Document",
        ("encrypt", "decrypt", "optimize", "compress_streams"),
    ),
    (
        "Run heuristic PDF/A and PDF/UA validation",
        "src/aspose_pdf/document.py",
        "Document",
        ("validate_pdfa", "validate_pdfua", "convert_to_pdfa", "convert_to_pdfua"),
    ),
)


def _pdf_rich_authoring_capability(root: Path) -> dict[str, object] | None:
    """Verify the composite text, drawing, annotation, attachment, and form surface."""

    components = (
        (
            "src/aspose_pdf/pages.py",
            "Page",
            {"add_text", "add_image", "draw_line", "draw_rectangle"},
        ),
        ("src/aspose_pdf/document.py", "Document", {"add_attachment"}),
        ("src/aspose_pdf/forms.py", "Form", {"add_text_field"}),
        ("src/aspose_pdf/annotations/__init__.py", "AnnotationCollection", {"add"}),
    )
    evidence: list[dict[str, object]] = []
    for relative, class_name, required in components:
        path = root / relative
        methods = _class_methods(path, class_name) if path.is_file() else set()
        if not required.issubset(methods):
            return None
        evidence.append(
            {
                "class": class_name,
                "methods": sorted(required),
                "source_path": relative,
                "source_sha256": _sha256(path),
            }
        )
    layout_path = root / "src/aspose_pdf/text_layout.py"
    features_path = root / "supported-features.md"
    if not layout_path.is_file() or not features_path.is_file():
        return None
    try:
        layout_tree = ast.parse(layout_path.read_text(encoding="utf-8"))
        features = features_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None
    if not any(
        isinstance(node, ast.ClassDef) and node.name == "TextLayoutOptions"
        for node in layout_tree.body
    ) or not all(
        marker in features.casefold()
        for marker in (
            "positioned standard-14 text or",
            "embedded unicode text with `page.add_text()`",
            "unicode bidi algorithm",
        )
    ):
        return None
    evidence.extend(
        [
            {
                "class": "TextLayoutOptions",
                "methods": [],
                "source_path": "src/aspose_pdf/text_layout.py",
                "source_sha256": _sha256(layout_path),
            },
            {
                "class": None,
                "methods": [],
                "source_path": "supported-features.md",
                "source_sha256": _sha256(features_path),
            },
        ]
    )
    return {
        "label": (
            "Add Standard-14 or embedded Unicode text, including shaped bidirectional text, "
            "plus images, lines, rectangles, annotations, attachments, and form data"
        ),
        "components": evidence,
    }


def _pdf_capability_details(root: Path) -> _CollectorResult | None:
    """Return visitor-facing PDF groups only when every named API exists in source."""

    groups: list[dict[str, object]] = []
    locations: list[str] = []
    for label, relative, class_name, required in _PDF_CAPABILITY_SPECS:
        path = root / relative
        methods = _class_methods(path, class_name) if path.is_file() else set()
        if not set(required).issubset(methods):
            continue
        groups.append(
            {
                "label": label,
                "class": class_name,
                "methods": list(required),
                "source_path": relative,
                "source_sha256": _sha256(path),
            }
        )
        locations.append(relative)
    rich_authoring = _pdf_rich_authoring_capability(root)
    if rich_authoring is not None:
        groups.append(rich_authoring)
        components = rich_authoring.get("components")
        if isinstance(components, list):
            locations.extend(
                str(item["source_path"])
                for item in components
                if isinstance(item, dict) and item.get("source_path")
            )
    render_test = root / "tests/test_page_rendering.py"
    render_source = root / "src/aspose_pdf/pages.py"
    output_formats: list[str] = []
    if render_test.is_file() and render_source.is_file():
        text = render_test.read_text(encoding="utf-8")
        methods = _class_methods(render_source, "Page")
        if "save_as_image" in methods and '"page.png"' in text and '"page.tiff"' in text:
            output_formats = ["PDF", "PNG", "TIFF"]
            locations.append("tests/test_page_rendering.py")
    if len(groups) < 6 or not output_formats:
        return None
    return (
        {
            "input_formats": ["PDF"],
            "output_formats": output_formats,
            "capability_groups": groups,
            "assurance": "source_api_and_test_corroborated",
        },
        sorted(set(locations)),
    )


def _pdf_verified_boundaries(root: Path) -> _CollectorResult | None:
    """Return exact PDF boundaries corroborated outside README prose."""

    features = root / "supported-features.md"
    source_paths = {
        "rendering": root / "src/aspose_pdf/pages.py",
        "reflow": root / "src/aspose_pdf/document.py",
        "pdfa": root / "src/aspose_pdf/pdfa.py",
        "pdfua": root / "src/aspose_pdf/pdfua.py",
        "signature": root / "src/aspose_pdf/signature.py",
        "compatibility": root / "src/aspose_pdf/exceptions.py",
    }
    if not features.is_file() or not all(path.is_file() for path in source_paths.values()):
        return None
    text = features.read_text(encoding="utf-8")
    required_documentation = (
        "contract is the active `tests/test_*.py` suite",
        "Layout reflow remains out of scope in this prerelease.",
        "OCR is not implemented.",
        "heuristic signals, not certification-grade",
    )
    source_text = {name: path.read_text(encoding="utf-8") for name, path in source_paths.items()}
    required_source = (
        "The renderer is dependency-free and supports common page content",
        "does not perform layout reflow",
        "not certification-grade PDF/A conformance",
        "not certification-grade PDF/UA conformance",
        "does **not** perform full PKCS#7 certificate chain checking",
        "Raised when a compatibility surface names a feature this package lacks",
    )
    corpus = "\n".join(source_text.values())
    if not all(marker in text for marker in required_documentation) or not all(
        marker in corpus for marker in required_source
    ):
        return None
    boundaries = [
        "Page rendering supports common page content; it is not represented as complete "
        "PDF graphics coverage.",
        "PDF/A and PDF/UA checks are heuristic signals, not certification-grade conformance.",
        "OCR is not implemented, and layout reflow remains outside the prerelease scope.",
        "The lightweight signature check does not perform full PKCS#7 certificate-chain "
        "validation.",
        "Compatibility surfaces may name features that are unavailable and must fail explicitly.",
        "The documented feature set is bounded by the active test suite rather than every "
        "exposed compatibility name.",
    ]
    locations = [
        "supported-features.md",
        *(path.relative_to(root).as_posix() for path in source_paths.values()),
    ]
    return (
        {
            "boundaries": boundaries,
            "evidence": [
                {"path": relative, "sha256": _sha256(root / relative)}
                for relative in sorted(set(locations))
            ],
            "assurance": "source_and_authoritative_feature_contract",
        },
        sorted(set(locations)),
    )


def _source(
    source_type: str,
    locations: list[str],
    source_revision: str | None,
    observed_at: str | None,
) -> FactSourceV2:
    return FactSourceV2(
        source_type=source_type,  # type: ignore[arg-type]
        location="repository://" + ",".join(locations),
        source_revision=source_revision,
        retrieved_at=observed_at,
    )


def _fact(
    field: str,
    qualifier: str,
    value: object,
    *,
    source_type: str,
    locations: list[str],
    source_revision: str | None,
    observed_at: str | None,
    affected_surfaces: list[str] | None = None,
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, qualifier),
        field=field,
        value=value,
        source=_source(source_type, locations, source_revision, observed_at),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=affected_surfaces or SURFACE_DEPENDENCIES[field],
    )


def curated_repository_fact_candidates(
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
) -> list[FactRecordV2]:
    """Return conservative, mechanically evidenced detail facts from one snapshot."""

    collectors = (
        (
            "installation.optional_extras",
            "python-manifest",
            "mechanical_manifest",
            python_optional_extras,
        ),
        (
            "installation.capability_dependencies",
            "python-source",
            "mechanical_repository",
            python_capability_dependencies,
        ),
        (
            "python.distribution",
            "pyproject-manifest",
            "mechanical_manifest",
            python_distribution_evidence,
        ),
        ("api.public_surface", "python-exports", "mechanical_repository", python_public_surface),
        (
            "repository.implementation_components",
            "python-implementation-components",
            "mechanical_repository",
            python_implementation_components,
        ),
        (
            "repository.examples",
            "repository-inventory",
            "mechanical_repository",
            lambda candidate_root: example_inventory(candidate_root, source_revision),
        ),
        (
            "repository.format_directions",
            "python-source-directions",
            "mechanical_repository",
            python_source_format_directions,
        ),
        (
            "repository.python_import_shadowing",
            "python-package-export-overrides",
            "mechanical_repository",
            python_import_shadowing,
        ),
        (
            "development.assets",
            "repository-inventory",
            "mechanical_repository",
            development_assets,
        ),
        (
            "development.commands",
            "repository-guidance",
            "mechanical_repository",
            repository_development_commands,
        ),
        (
            "repository.documentation_assets",
            "root-documents",
            "mechanical_repository",
            repository_documentation_assets,
        ),
        (
            "repository.security_guidance",
            "security-policy-and-source",
            "mechanical_repository",
            repository_security_guidance,
        ),
        (
            "repository.contribution_guidance",
            "repository-entry-points",
            "mechanical_repository",
            repository_contribution_guidance,
        ),
        (
            "repository.third_party_notices",
            "root-notices-file",
            "mechanical_repository",
            third_party_notices,
        ),
        ("repository.ci", "canonical-workflow", "mechanical_repository", repository_ci),
        (
            "product.limitations",
            "source-guidance",
            "mechanical_repository",
            source_guidance_limitations,
        ),
        (
            "repository.capability_details",
            "python-public-source-surfaces",
            "mechanical_repository",
            _pdf_capability_details,
        ),
        (
            "repository.verified_boundaries",
            "authoritative-source-and-tests",
            "mechanical_repository",
            _pdf_verified_boundaries,
        ),
    )
    facts: list[FactRecordV2] = []
    for field, qualifier, source_type, collector in collectors:
        result: _CollectorResult | None = collector(root)
        if result is None:
            continue
        value, locations = result
        affected_surfaces = {
            "repository.capability_details": ["readme.capabilities", "readme.examples"],
            "repository.implementation_components": ["readme.opening", "readme.api_reference"],
            "repository.format_directions": ["readme.capabilities"],
            "repository.python_import_shadowing": ["readme.api"],
            "repository.verified_boundaries": ["readme.limitations", "readme.security"],
        }.get(field)
        facts.append(
            _fact(
                field,
                qualifier,
                value,
                source_type=source_type,
                locations=locations,
                source_revision=source_revision,
                observed_at=observed_at,
                affected_surfaces=affected_surfaces,
            )
        )
    return facts
