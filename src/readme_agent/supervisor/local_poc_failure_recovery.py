"""Seal partial local-POC evidence at recoverable transaction boundaries."""

from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums


def seal_partial_local_poc_evidence(bundle_dir: Path) -> None:
    """Bind completed artifacts so a later canonical transaction can resume safely."""

    refresh_sha256sums(bundle_dir)
