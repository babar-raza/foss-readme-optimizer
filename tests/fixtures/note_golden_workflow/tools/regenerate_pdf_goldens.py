from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from aspose.note import Document
from aspose.note.saving import PdfSaveOptions
from tests._pdf_goldens import (
    PDF_GOLDEN_CASES,
    build_pdf_manifest,
    ensure_output_dirs,
    fixture_path,
    golden_manifest_path,
    golden_pdf_path,
    write_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate semantic PDF goldens.")
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="Case id to regenerate. Can be passed multiple times.",
    )
    return parser.parse_args()


def selected_cases(case_ids: list[str] | None) -> list:
    if not case_ids:
        return list(PDF_GOLDEN_CASES)
    allowed = {case.case_id: case for case in PDF_GOLDEN_CASES}
    unknown = [case_id for case_id in case_ids if case_id not in allowed]
    if unknown:
        raise SystemExit(f"Unknown case ids: {', '.join(sorted(unknown))}")
    return [allowed[case_id] for case_id in case_ids]


def main() -> int:
    args = parse_args()
    ensure_output_dirs()

    for case in selected_cases(args.cases):
        source = fixture_path(case.fixture_name)
        if source is None:
            raise SystemExit(f"Missing fixture: {case.fixture_name}")

        output_pdf = golden_pdf_path(case.case_id)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        Document(source).Save(str(output_pdf), PdfSaveOptions())

        manifest = build_pdf_manifest(output_pdf, fixture_name=case.fixture_name)
        write_manifest(golden_manifest_path(case.case_id), manifest)
        print(f"updated {case.case_id}: {output_pdf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())