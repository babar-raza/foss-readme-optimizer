"""README candidates fail closed on false package claims and protected loss."""

from types import SimpleNamespace

from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.specialists import readme_factuality


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
