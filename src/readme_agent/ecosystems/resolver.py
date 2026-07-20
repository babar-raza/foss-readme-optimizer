"""Live package-registry resolution, dispatched by ecosystem string -- mirrors
ecosystems/registry.py's "new ecosystems are new entries, not new call sites"
contract. Opt-in only: never called by default -- see links/validator.py for
the established pattern of live network checks staying opt-in, WARNING-only,
never a default hard gate.

Maven implemented first (Java is the only ecosystem with a shipped manifest
parser today); Python is next in priority by repository count (10 of 25
registry entries), not before -- see the portfolio-survey finding this
session recorded (plans/investigations/full-registry-portfolio-survey.md).

This is the concrete mechanism that would have caught the real cells-java
finding automatically: its README instructs a Maven Central dependency
(org.aspose:aspose-cells-foss) that returns zero results.
"""

from dataclasses import dataclass

import requests

_MAVEN_CENTRAL_SEARCH_URL = "https://search.maven.org/solrsearch/select"


@dataclass
class ResolutionResult:
    found: bool
    detail: str


def _resolve_maven(manifest: dict[str, str], timeout: float = 10) -> ResolutionResult:
    group_id = manifest.get("group_id")
    artifact_id = manifest.get("artifact_id")
    if not group_id or not artifact_id:
        return ResolutionResult(False, "manifest missing group_id/artifact_id -- cannot resolve")
    try:
        resp = requests.get(
            _MAVEN_CENTRAL_SEARCH_URL,
            params={"q": f"g:{group_id} AND a:{artifact_id}", "rows": "1", "wt": "json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        found = resp.json()["response"]["numFound"] > 0
        return ResolutionResult(
            found,
            f"Maven Central: {group_id}:{artifact_id} "
            f"{'found' if found else 'NOT FOUND (0 results)'}",
        )
    except requests.RequestException as exc:
        return ResolutionResult(False, f"network error resolving Maven Central: {exc}")
    except (KeyError, ValueError) as exc:
        return ResolutionResult(False, f"unexpected Maven Central response shape: {exc}")


_RESOLVERS = {
    "java": _resolve_maven,
}


def resolve(ecosystem: str, manifest: dict[str, str]) -> ResolutionResult:
    resolver = _RESOLVERS.get(ecosystem)
    if resolver is None:
        return ResolutionResult(False, f"no live resolver registered for ecosystem {ecosystem!r}")
    return resolver(manifest)
