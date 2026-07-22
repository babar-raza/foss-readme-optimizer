"""Wave 8.6: periodic (not per-run) capability -- re-fetches the reference
repositories `docs/presentation-standard.md`'s own research was based on, so
a periodic script (not the main per-run supervisor loop) can flag when their
real README content has drifted from what the codified standard's own text
describes. Deliberately NOT wired into the specialist tier: re-fetching five
external repositories live every supervise run would add an uncontrolled
external network dependency for no per-run benefit -- this capability exists
to be called on a schedule, by a script, not by the planner.

Read-only, stateless (decision #26(b)): returns each reference repo's
current README content hash; comparing that hash against a previously
observed one (to detect drift) is the calling script's job, not this
capability's -- it has no persisted baseline of its own to compare against."""

from readme_agent.capabilities.domains import PRESENTATION_BENCHMARKING
from readme_agent.capabilities.schema import CapabilityManifest
from readme_agent.env import gh_token
from readme_agent.github_api.client import get_file_content
from readme_agent.readme.facts import sha256_text

CAPABILITY_ID = "compare_reference_repositories"

# The six real, live sources `docs/presentation-standard.md`'s own "Sources
# studied" section names -- GitHub-hosted ones only (Aspose.Cells on NuGet
# has no README to fetch this way, and this project's own registry is
# already covered by every other capability).
REFERENCE_REPOSITORIES: dict[str, str] = {
    "n8n": "n8n-io/n8n",
    "itext": "itext/itext7",
    "epplus": "EPPlusSoftware/EPPlus",
    "sheetjs": "SheetJS/sheetjs",
    "pdfbox": "apache/pdfbox",
}

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Compare reference repositories",
    purpose="Read-only: re-fetches the README content of the reference repositories "
    "docs/presentation-standard.md's own research was based on, returning a content hash per "
    "repository. Intended for periodic/scheduled invocation, never the per-run supervisor "
    "loop -- drift detection (comparing against a previously observed hash) is the calling "
    "script's job, not this capability's.",
    category="presentation_benchmarking",
    owner="readme_agent.capabilities.compare_reference_repositories",
    execution_type="read_only_audit",
    required_inputs={},
    produced_outputs={"reference_readme_hashes": "object"},
    preconditions=["intended for periodic/scheduled invocation, not the per-run planner loop"],
    required_permissions=["read_only_network"],
    side_effect_class="read_only_network",
    allowed_domains=[PRESENTATION_BENCHMARKING],
    tools_used=["github_api.client.get_file_content"],
    failure_modes=[
        "a single reference repo's fetch failure is recorded per-repo, never aborts the "
        "whole call -- one unreachable reference source should not hide the other five"
    ],
    rollback_behavior="not applicable -- read-only, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
)


def execute() -> dict:
    token = gh_token()
    hashes: dict[str, str | None] = {}
    for name, org_repo in REFERENCE_REPOSITORIES.items():
        try:
            content = get_file_content(org_repo, "README.md", token)
        except Exception as exc:  # noqa: BLE001 -- one unreachable reference must not hide the rest
            hashes[name] = f"ERROR:{exc}"
            continue
        hashes[name] = sha256_text(content.decode("utf-8", errors="replace"))
    return {"reference_readme_hashes": hashes}
