"""README candidates fail closed on false package claims and protected loss."""

import json
from pathlib import Path
from types import SimpleNamespace

from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.specialists import readme_factuality

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPLETE_FACTS_PROOF = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts_result():
    v1 = ProductFactsV1(
        org_repo="acme/widget",
        family="widget",
        platform="java",
        ecosystem="java",
    )
    v2 = migrate_product_facts_v1(v1, source_revision="abc123")
    return {
        "org_repo": "acme/widget",
        "family": "widget",
        "platform": "java",
        "ecosystem": "java",
        "declared_license": "MIT",
        "package_roots": [
            {
                "path": ".",
                "ecosystem": "java",
                "manifest_path": "pom.xml",
            }
        ],
        "relationship_talking_points": [],
        "secondary_links": [],
        "unresolved_manifests": [],
        "product_facts_v2": v2.model_dump(mode="json"),
    }


def _complete_snapshot_facts() -> ProductFactsV2:
    proof = json.loads(COMPLETE_FACTS_PROOF.read_text(encoding="utf-8"))
    pilot = next(
        item
        for item in proof["current_pilots"]
        if item["org_repo"] == "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    )
    return ProductFactsV2.model_validate(pilot["product_facts_v2"])


def _mock_dispatch(monkeypatch, acquisition_outcome="REGISTRY_VERIFIED"):
    def dispatch(tool_call, permissions):
        name = tool_call["function"]["name"]
        if name == "get_product_facts":
            return SimpleNamespace(outcome="executed", result=_facts_result(), error=None)
        if name == "verify_package_acquisition":
            return SimpleNamespace(
                outcome="executed",
                result={
                    "results": [
                        {
                            "path": ".",
                            "ecosystem": "java",
                            "outcome": acquisition_outcome,
                            "detail": f"Maven Central: {acquisition_outcome}",
                        }
                    ]
                },
                error=None,
            )
        raise AssertionError(name)

    monkeypatch.setattr(readme_factuality, "dispatch_tool_call", dispatch)


def test_known_false_maven_coordinate_rejects_candidate(monkeypatch):
    _mock_dispatch(monkeypatch, acquisition_outcome="NOT_PUBLISHED")
    readme = """# Widget

```xml
<dependency>
  <groupId>org.acme</groupId>
  <artifactId>made-up</artifactId>
</dependency>
```
"""

    decision = readme_factuality.evaluate_candidate_factuality(
        "acme/widget", readme, readme, {"read_only_local", "read_only_network"}
    )

    assert decision.valid is False
    assert decision.claim_conflicts[0]["claimed_coordinate"] == "org.acme:made-up"


def test_protected_command_loss_rejects_candidate(monkeypatch):
    _mock_dispatch(monkeypatch)
    before = "# Widget\n\n```bash\npip install widget\n```\n"
    after = "# Widget\n\nInstall Widget.\n"

    decision = readme_factuality.evaluate_candidate_factuality(
        "acme/widget", before, after, {"read_only_local", "read_only_network"}
    )

    assert decision.valid is False
    assert any(loss["category"] == "command" for loss in decision.protected_content_losses)


def test_owned_span_only_change_with_verified_package_is_accepted(monkeypatch):
    _mock_dispatch(monkeypatch)
    before = "# Widget\n"
    after = (
        '# Widget\n\n<!-- readme-agent:resources hash="sha256:abc" schema="2" -->\n'
        "Resources\n<!-- readme-agent:resources:end -->\n"
    )

    decision = readme_factuality.evaluate_candidate_factuality(
        "acme/widget", before, after, {"read_only_local", "read_only_network"}
    )

    assert decision.valid is True
    assert decision.product_facts_v2_hash is not None


def test_fact_dispatch_failure_rejects_before_verifier(monkeypatch):
    monkeypatch.setattr(
        readme_factuality,
        "dispatch_tool_call",
        lambda tool_call, permissions: SimpleNamespace(
            outcome="failed", result=None, error="state unavailable"
        ),
    )

    decision = readme_factuality.evaluate_candidate_factuality(
        "acme/widget", "# Widget\n", "# Widget\n", {"read_only_local"}
    )

    assert decision.valid is False
    assert decision.error == "get_product_facts:failed:state unavailable"


def test_snapshot_bound_v2_facts_do_not_reobserve_network(monkeypatch):
    facts = _complete_snapshot_facts()
    source = "# Widget\n"
    candidate, _plan = build_readme_document_candidate(
        facts.org_repo,
        source,
        facts,
        base_revision=facts.selected_fact("product.identity").source.source_revision or "",
    )

    def unexpected_dispatch(*_args, **_kwargs):
        raise AssertionError("snapshot-bound factuality must not re-dispatch fact collectors")

    monkeypatch.setattr(readme_factuality, "dispatch_tool_call", unexpected_dispatch)
    decision = readme_factuality.evaluate_candidate_factuality(
        facts.org_repo,
        source,
        candidate,
        {"read_only_local", "read_only_network"},
        source_text=source,
        product_facts_v2=facts,
    )

    assert decision.valid is True
    assert decision.claim_conflicts == []
