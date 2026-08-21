#!/usr/bin/env python3
"""Audit portfolio knowledge selection from current refresh receipts."""

from __future__ import annotations

import argparse
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.portfolio_knowledge_selection import (
    audit_portfolio_knowledge_selection,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-receipt", action="append", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    report = audit_portfolio_knowledge_selection(
        tuple(args.refresh_receipt),
        output_dir=args.output_dir,
    )
    write_redacted_json(args.output_dir / "receipt.json", report)
    refresh_sha256sums(args.output_dir)
    print(
        f"knowledge selection: processable={report.processable}, "
        f"disposed={report.typed_dispositions}, failed={report.failed}, "
        f"claims={report.total_claims}, selected={report.total_selected}"
    )
    if report.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
