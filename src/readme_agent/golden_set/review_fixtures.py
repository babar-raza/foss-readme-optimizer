"""Heterogeneous products and ProductFactsV2 fixtures for reviewer qualification."""

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import REQUIRED_PRODUCT_FIELDS


@dataclass(frozen=True)
class ReviewArchetype:
    ecosystem: str
    product: str
    audience: str
    capability: str
    format_name: str
    acquisition: str
    example: str
    limitation: str
    conflicting_claim: str


REVIEW_ARCHETYPES = (
    ReviewArchetype(
        "java",
        "AcmeCells Java",
        "Java backend developers generating spreadsheets",
        "read and write XLSX workbooks",
        "XLSX",
        "Maven coordinate com.acme:acme-cells:1.4.0",
        'Workbook.load("input.xlsx").save("output.xlsx")',
        "does not execute VBA macros",
        "executes VBA macros",
    ),
    ReviewArchetype(
        "dotnet",
        "Acme3D .NET",
        ".NET developers transforming 3D assets",
        "load and save OBJ meshes",
        "OBJ",
        "NuGet package Acme.ThreeD 2.1.0",
        'Scene.FromFile("input.obj").Save("output.obj")',
        "does not render raster images",
        "renders raster images",
    ),
    ReviewArchetype(
        "python",
        "AcmePDF Python",
        "Python developers extracting text from PDFs",
        "extract text from text-based PDF pages",
        "PDF",
        "PyPI package acme-pdf 3.0.0",
        'Document("input.pdf").pages[0].text',
        "does not perform OCR",
        "performs OCR",
    ),
    ReviewArchetype(
        "typescript",
        "AcmeCells TypeScript",
        "Node.js developers inspecting spreadsheets",
        "parse XLSX worksheet values in Node.js",
        "XLSX",
        "npm package @acme/cells 1.2.0",
        'const book = await Workbook.load("input.xlsx")',
        "does not run in a browser",
        "runs in a browser",
    ),
    ReviewArchetype(
        "cpp",
        "AcmeSlides C++",
        "C++ developers inspecting presentations",
        "read PPTX slide titles",
        "PPTX",
        "source build with CMake; no registry package is published",
        'Presentation deck("input.pptx"); deck.slide(0).title()',
        "does not render slide previews",
        "renders slide previews",
    ),
    ReviewArchetype(
        "go",
        "AcmePDF Go",
        "Go developers splitting PDF documents",
        "split unencrypted PDFs by page range",
        "PDF",
        "Go module github.com/acme/pdf-go@v0.8.0",
        'pdf.Open("input.pdf").Pages(1, 2).Save("part.pdf")',
        "does not open encrypted PDFs",
        "opens encrypted PDFs",
    ),
    ReviewArchetype(
        "rust",
        "AcmeCells Rust",
        "Rust developers reading spreadsheet metadata",
        "read XLSX worksheet names",
        "XLSX",
        "Cargo crate acme-cells 0.6.0",
        'Workbook::open("input.xlsx")?.sheet_names()',
        "does not recalculate formulas",
        "recalculates formulas",
    ),
)


def build_review_facts(archetype: ReviewArchetype) -> dict:
    values = {
        "product.identity": {"name": archetype.product, "ecosystem": archetype.ecosystem},
        "product.audience": archetype.audience,
        "product.problems_solved": [f"Use code to {archetype.capability}"],
        "product.capabilities": [archetype.capability],
        "product.formats": [archetype.format_name],
        "product.platforms": [archetype.ecosystem],
        "installation.coordinates": None
        if "source build" in archetype.acquisition
        else archetype.acquisition,
        "installation.verified_acquisition": archetype.acquisition,
        "example.minimal": archetype.example,
        "documentation.links": ["https://example.invalid/golden-set/docs"],
        "release.state": "active",
        "product.limitations": [archetype.limitation],
        "product.compatibility": [archetype.ecosystem, archetype.format_name],
        "product.license": "Apache-2.0",
        "support.routes": ["https://example.invalid/golden-set/issues"],
        "relationship.commercial_foss": (
            "The Apache-2.0 FOSS repository is usable independently of a separate commercial "
            "product."
        ),
    }
    if set(values) != set(REQUIRED_PRODUCT_FIELDS):
        raise ValueError("review golden facts do not cover the ProductFactsV2 inventory")
    return {
        "schema_version": 2,
        "org_repo": f"golden-set/{archetype.product.replace(' ', '-')}",
        "facts": [
            {
                "fact_id": f"{field}:golden",
                "field": field,
                "value": value,
                "verification_state": "missing" if value is None else "verified",
                "source": {
                    "source_type": "mechanical_repository",
                    "location": f"golden-set://{archetype.ecosystem}/{field}",
                    "source_revision": "golden-set-revision",
                },
                "authoritative_owner": "golden-set-fixture",
                "confidence": 0.0 if value is None else 1.0,
                "conflicts": [],
                "affected_surfaces": ["readme"],
            }
            for field, value in values.items()
        ],
        "selected_fact_ids": {field: f"{field}:golden" for field in values},
    }


def with_package_roots(facts: dict) -> dict:
    roots_fact = {
        "fact_id": "repository.package_roots:golden",
        "field": "repository.package_roots",
        "value": ["packages/core", "packages/node-adapter"],
        "verification_state": "verified",
        "source": {
            "source_type": "mechanical_repository",
            "location": "golden-set://typescript/repository.package_roots",
            "source_revision": "golden-set-revision",
        },
        "authoritative_owner": "golden-set-fixture",
        "confidence": 1.0,
        "conflicts": [],
        "affected_surfaces": ["readme"],
    }
    return {**facts, "facts": [*facts["facts"], roots_fact]}


def specific_candidate(archetype: ReviewArchetype) -> str:
    return (
        f"# {archetype.product}\n\n{archetype.product} helps {archetype.audience} to "
        f"{archetype.capability}.\n\n## Install\n{archetype.acquisition}.\n\n"
        f"## Minimal example\n```\n{archetype.example}\n```\n\n"
        f"## Supported format\n- {archetype.format_name}\n\n"
        f"## Limitation\n- It {archetype.limitation}.\n\n"
        "## Documentation and support\n"
        "- Documentation: https://example.invalid/golden-set/docs\n"
        "- Issues: https://example.invalid/golden-set/issues\n\n"
        "## Maintenance\nThis project is active.\n\n"
        "## FOSS and commercial products\n"
        "The Apache-2.0 FOSS repository is usable independently of a separate "
        "commercial product.\n\n"
        "## License\nApache-2.0\n"
    )
