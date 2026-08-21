#!/usr/bin/env python3
"""Generate offline portfolio README diagnostics from current selected knowledge."""

from __future__ import annotations

import argparse
from pathlib import Path

from readme_agent.facts.portfolio_knowledge_qualification import qualify_portfolio_knowledge

_DEFAULT_SELECTION = Path(
    "runs/multi-agent/L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY/portfolio-selection/receipt.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-receipt", type=Path, default=_DEFAULT_SELECTION)
    parser.add_argument("--output-root", type=Path, default=Path("runs/knowledge-qualification"))
    args = parser.parse_args()
    report = qualify_portfolio_knowledge(
        args.selection_receipt,
        output_root=args.output_root,
    )
    print(
        "knowledge qualification: "
        f"candidates={report.candidate_generated}/{report.processable}, "
        f"document_valid={report.document_valid}, "
        f"current_contract={report.qualified_current_contract}, "
        f"stale_contract={report.qualified_stale_contract}"
    )


if __name__ == "__main__":
    main()
