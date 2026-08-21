#!/usr/bin/env python3
"""Refresh a disjoint allow-listed repository-knowledge cohort."""

from __future__ import annotations

import argparse
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.portfolio_knowledge_refresh import refresh_repository_knowledge_cohort


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", required=True, help="Comma-separated exact org/repo values")
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    repositories = tuple(value.strip() for value in args.only.split(",") if value.strip())
    if not repositories or len(repositories) != len(set(repositories)):
        raise SystemExit("--only must contain unique repository coordinates")

    report = refresh_repository_knowledge_cohort(repositories)
    write_redacted_json(args.receipt, report)
    refresh_sha256sums(args.receipt.parent)
    current = sum(entry.status == "current" for entry in report.entries)
    failed = sum(entry.status == "failed" for entry in report.entries)
    disposed = sum(entry.status == "non_processable_no_implementation" for entry in report.entries)
    print(f"knowledge refresh: current={current}, disposed={disposed}, failed={failed}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
