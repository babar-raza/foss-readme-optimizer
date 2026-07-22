"""Wave 8.6 (item I, `LLM-017`/`VAL-016`/`RDM-020`) -- periodic, standalone
batch job: computes pairwise embedding similarity across the enabled
portfolio's real, live READMEs, flagging likely template-clone/generic-prose
pairs. Deliberately NOT run by the per-run supervisor loop -- `LLM-017`'s own
text: "a new periodic batch script, explicitly kept out of the per-run
supervisor planner loop."

Strips every owned span (`readme/markers.py::SPAN_NAMES`, the same mechanism
`readme/reconciliation.py`'s own drift classifier already uses) before
embedding, so only genuinely-authored prose is compared -- shared, policy-
mandated boilerplate never counts as a "clone" on its own.

Output: `data/template_clone_findings.json`, consumed by the
`get_template_clone_findings` capability (`src/readme_agent/capabilities/
get_template_clone_findings.py`) for a given org_repo, or read directly by a
human. Never treated as a sole verdict -- evidence only.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from readme_agent import env  # noqa: E402
from readme_agent.github_api.client import get_file_content  # noqa: E402
from readme_agent.llm.embeddings_client import get_embedding  # noqa: E402
from readme_agent.readme.markers import SPAN_NAMES, remove_span  # noqa: E402
from readme_agent.registry.loader import enabled_entries  # noqa: E402

# Wave 8.6: the live characterization evidence (`llm-gateway-characterization.
# md` L4) showed a known same-template pair at cosine 0.788 and unrelated
# pairs at 0.45-0.55 -- this sits between the two, closer to the known-clone
# side, since it's the only real data point available. No operational
# history yet to justify a different value -- revisit once this script has
# run enough real portfolio passes to have its own evidence.
SIMILARITY_THRESHOLD = 0.70

OUTPUT_PATH = REPO_ROOT / "data" / "template_clone_findings.json"


def _strip_owned_spans(text: str) -> str:
    stripped = text
    for span_name in SPAN_NAMES:
        stripped = remove_span(stripped, span_name)
    return stripped


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def compute_embeddings(org_repos: list[str], token: str | None) -> dict[str, list[float] | None]:
    base_url = env.llm_base_url()
    api_key = env.llm_api_key()
    model = env.llm_embedding_model()
    embeddings: dict[str, list[float] | None] = {}
    for org_repo in org_repos:
        try:
            content = get_file_content(org_repo, "README.md", token).decode(
                "utf-8", errors="replace"
            )
            stripped = _strip_owned_spans(content)
            embeddings[org_repo] = get_embedding(stripped, model, base_url, api_key)
        except Exception as exc:  # noqa: BLE001 -- one repo's failure must not abort the batch
            print(f"warning: could not embed {org_repo}: {exc}", file=sys.stderr)
            embeddings[org_repo] = None
    return embeddings


def find_flagged_pairs(
    embeddings: dict[str, list[float] | None], threshold: float = SIMILARITY_THRESHOLD
) -> list[dict]:
    flagged = []
    available = {repo: vec for repo, vec in embeddings.items() if vec is not None}
    for repo_a, repo_b in itertools.combinations(sorted(available), 2):
        similarity = _cosine_similarity(available[repo_a], available[repo_b])
        if similarity >= threshold:
            flagged.append(
                {"repo_a": repo_a, "repo_b": repo_b, "cosine_similarity": round(similarity, 4)}
            )
    return flagged


def main() -> None:
    entries = enabled_entries()
    org_repos = [entry.org_repo for entry in entries]
    token = env.gh_token()

    embeddings = compute_embeddings(org_repos, token)
    flagged_pairs = find_flagged_pairs(embeddings)

    findings = {
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "repos_embedded": sorted(repo for repo, vec in embeddings.items() if vec is not None),
        "repos_failed": sorted(repo for repo, vec in embeddings.items() if vec is None),
        "flagged_pairs": flagged_pairs,
    }
    OUTPUT_PATH.write_text(json.dumps(findings, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATH} -- {len(flagged_pairs)} flagged pair(s)")


if __name__ == "__main__":
    main()
