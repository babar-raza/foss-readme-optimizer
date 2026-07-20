# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Reconciliation prototype: three-way (base / accepted-presentation / current-upstream
+ Facts + Policy) reconciliation with a durable .state/ store, drift classification,
generation cache, concurrency check, and a verified second-run no-op. Never pushes;
apply = prepared patch only.

Design points demonstrated here (mapping to the governed docs):
- upstream is read FRESH every run (fixes the input-acquisition boundary the shipped
  tool suffers from);
- product-agent output is an upstream DRAFT; we recompile desired state from
  current-upstream + Facts + Policy — never blind-replay the old base->accepted patch,
  never auto-revert;
- raw-bytes section preservation (marko round-trip proved lossy 7/14) with
  markdown-it-py token.map used for ANALYSIS only;
- missing facts / claim conflicts => BLOCKED_PENDING_PRODUCT_OWNER handoff;
- fingerprint-keyed generation cache => rerun makes ZERO LLM calls;
- remote-HEAD compare-and-swap before apply => STALE_INPUT on movement;
- community files ride the same spine (COMMUNITY_FILE_DRIFT + restore proposal).
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
from readme_agent.readme.gap_detector import detect as detect_gaps  # noqa: E402
from readme_agent.registry.models import PolicyProfile  # noqa: E402

TOOL_VERSION = "reconciliation-prototype-1"
MD = MarkdownIt()


def sha(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def git_head(repo: Path) -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True)
    return out.stdout.strip()


# ---------------------------------------------------------------- state store
class StateStore:
    """Durable per-repo presentation state: .state/<key>.json, atomic writes."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def load(self, key: str) -> dict | None:
        p = self.path(key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def save(self, key: str, state: dict) -> None:
        p = self.path(key)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.replace(tmp, p)  # atomic (proven pattern from evidence/writer.py)


# ------------------------------------------------------------------- analysis
def sections(readme: str) -> list[dict]:
    """Raw-bytes-preserving section split using markdown-it token.map (analysis only)."""
    lines = readme.split("\n")
    heads = [
        (t.map[0], t.tag, lines[t.map[0]].lstrip("# ").strip())
        for t in MD.parse(readme)
        if t.type == "heading_open" and t.map
    ]
    out = []
    for i, (start, tag, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(lines)
        out.append({"title": title, "tag": tag, "raw": "\n".join(lines[start:end])})
    return out


def claimed_capabilities(readme: str) -> list[str]:
    """Bullet lines under a Features/Capabilities heading (markdown-it analysis)."""
    caps: list[str] = []
    for s in sections(readme):
        if any(k in s["title"].lower() for k in ("feature", "capabilit")):
            caps += [
                ln.lstrip("-* ").strip()
                for ln in s["raw"].split("\n")
                if ln.strip().startswith(("-", "*"))
            ]
    return caps


def similarity(a: str, b: str) -> float:
    """Offline proxy for embedding cosine (production: qwen3-embedding-8b, finding L4)."""
    return difflib.SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------- LLM w/cache
def relationship_paragraph(
    facts: dict,
    policy: PolicyProfile,
    state: dict | None,
    fingerprint: str,
    live: bool,
    fixture_path: Path,
    counters: dict,
) -> str:
    """Generation-cache-first: reuse validated cached output for the same fingerprint.
    Live path routes to qwen3-next (finding L2: never gpt-oss for instruction-critical),
    falls back to fixture on any failure. Every output is length/term validated."""
    cache = (state or {}).get("generation_cache", {})
    if cache.get("fingerprint") == fingerprint and cache.get("paragraph"):
        counters["llm_calls_avoided_by_cache"] += 1
        return cache["paragraph"]
    text = ""
    if live:
        try:
            import requests

            from readme_agent import env

            r = requests.post(
                f"{env.llm_base_url().rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {env.llm_api_key()}"},
                json={
                    "model": "qwen3-next",
                    "temperature": 0.0,
                    "max_tokens": 220,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "Write one plain prose paragraph (35-90 words, no "
                                "links, no markdown) explaining that "
                                f"{facts['product']} is the open-source edition and "
                                "that a commercial edition with more features "
                                "exists. Mention both the open source scope and "
                                "the commercial upgrade path."
                            ),
                        }
                    ],
                },
                timeout=60,
            )
            if r.status_code == 200:
                text = (r.json()["choices"][0]["message"]["content"] or "").strip()
                counters["llm_calls_live"] += 1
        except Exception:  # noqa: BLE001 -- fixture fallback below
            text = ""
    if not text:
        text = json.loads(fixture_path.read_text(encoding="utf-8"))["relationship_paragraph"]
        counters["llm_calls_fixture"] += 1
    words = len(text.split())
    lo, hi = policy.block.word_limit.min, policy.block.word_limit.max
    if not (lo <= words <= hi):  # validation backstop; fall back to fixture
        text = json.loads(fixture_path.read_text(encoding="utf-8"))["relationship_paragraph"]
    return text


def render_resources_span(
    gaps, policy: PolicyProfile, paragraph: str | None, fingerprint: str
) -> str:
    """Deterministic policy-URL rendering (URLs from policy, never from the model)."""
    # GapReport polarity: True = element PRESENT; render only what is MISSING.
    lines = [
        f'<!-- central-agent:resources fp="sha256:{fingerprint[:16]}" v="1" -->',
        "",
        "## Resources",
        "",
    ]
    org = policy.required_elements.products_org_link
    com = policy.required_elements.products_com_link
    if not gaps.products_org_link:
        lines.append(f"- [{org.label}]({org.url})")
    if not gaps.products_com_link:
        utm = "&".join(f"{k}={v}" for k, v in (com.utm or {}).items())
        sep = "&" if "?" in com.url else "?"
        lines.append(
            f"- [{com.label}]({com.url}{sep}{utm})" if utm else f"- [{com.label}]({com.url})"
        )
    if not gaps.relationship_explained and paragraph:
        lines += ["", paragraph]
    lines += ["", "<!-- central-agent:resources:end -->"]
    return "\n".join(lines)


# ------------------------------------------------------------------- the loop
@dataclass
class Result:
    status: str
    drift: str
    llm: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)
    handoff: dict | None = None
    candidate_path: str | None = None
    patch_path: str | None = None
    notes: list[str] = field(default_factory=list)


def run_reconciliation(
    source_repo: Path,
    policy: PolicyProfile,
    facts: dict,
    state_key: str,
    state_root: Path,
    work_root: Path,
    fixture_llm: Path,
    live_llm: bool = False,
    head_advancer=None,
    new_tokens: list[str] | None = None,
) -> Result:
    """One reconciliation run. head_advancer: optional callable fired between candidate
    creation and apply (simulates concurrent product-agent push).
    new_tokens: strings that exist ONLY in the current upstream (never in base/accepted);
    the candidate MUST contain them — the independent, non-tautological proof that
    reconciliation operated on fresh upstream (contrast: shipped tool sees_new_content=False)."""
    store = StateStore(state_root)
    state = store.load(state_key)
    counters = {"llm_calls_live": 0, "llm_calls_fixture": 0, "llm_calls_avoided_by_cache": 0}

    # 1. SNAPSHOT — upstream read FRESH every run (fixes the input-acquisition boundary)
    head = git_head(source_repo)
    upstream = (source_repo / "README.md").read_text(encoding="utf-8")
    contributing = source_repo / "CONTRIBUTING.md"
    upstream_files = {
        "CONTRIBUTING.md": contributing.read_text(encoding="utf-8")
        if contributing.exists()
        else None
    }

    # 2. FACTS_VALIDATED — claims in the upstream draft vs authoritative facts
    facts_hash = sha(json.dumps(facts, sort_keys=True))
    policy_hash = sha(policy.model_dump_json())
    claimed = claimed_capabilities(upstream)
    known = [c.lower() for c in facts.get("capabilities", [])]
    conflicts = [c for c in claimed if not any(k in c.lower() or c.lower() in k for k in known)]
    if conflicts:
        return Result(
            status="BLOCKED_PENDING_PRODUCT_OWNER",
            drift="CONFLICTING_FACTS",
            handoff={
                "finding": "readme_claims_capability_not_in_product_facts",
                "claims": conflicts,
                "source_commit": head,
                "facts_hash": facts_hash,
                "owner": facts.get("owner", "product-agent"),
                "required_action": "confirm capability + refresh ProductFacts, or correct README",
            },
            notes=[
                "No candidate produced; the central agent never invents or endorses "
                "an unverified capability (FACT-004)."
            ],
        )

    # 3. Fingerprint + no-op check (surface idempotency)
    fingerprint = sha("|".join([head, sha(upstream), facts_hash, policy_hash, TOOL_VERSION]))
    if state and state.get("fingerprint") == fingerprint:
        accepted = state["accepted_output"]
        current = (
            (work_root / "README.md").read_text(encoding="utf-8")
            if (work_root / "README.md").exists()
            else None
        )
        if current == accepted:
            return Result(
                status="NO_CHANGE",
                drift="NO_CHANGE",
                llm=counters,
                checks={"fingerprint_match": True, "output_match": True, "llm_calls_this_run": 0},
                notes=[
                    "Verified no-op: fingerprint + accepted output both match; "
                    "zero LLM calls, zero writes."
                ],
            )

    # 4. DRIFT_CLASSIFIED — three-way base / accepted / current-upstream comparison
    base = state.get("upstream_base") if state else None
    accepted = state.get("accepted_output") if state else None
    drift, dnotes = "NO_CHANGE", []
    if state:
        upstream_changed = base != upstream
        sim_up_base = similarity(upstream, base or "")
        sim_up_acc = similarity(upstream, accepted or "")

        # Both marker families: legacy shipped spans (readme-agent:*) and this
        # prototype's spans (central-agent:*). A span is "lost" only if the accepted
        # output had an intact begin+end pair that upstream no longer carries intact.
        def _intact(text: str, fam: str) -> bool:
            return f"{fam}:resources" in text and f"{fam}:resources:end" in text

        spans_lost = accepted is not None and any(
            _intact(accepted, fam) and not _intact(upstream, fam)
            for fam in ("readme-agent", "central-agent")
        )

        if upstream_files["CONTRIBUTING.md"] is None and (state.get("accepted_files") or {}).get(
            "CONTRIBUTING.md"
        ):
            drift = "COMMUNITY_FILE_DRIFT"
            dnotes.append("CONTRIBUTING.md removed upstream but exists in accepted state")
        elif upstream_changed and spans_lost:
            drift = "MIXED_CHANGE" if sim_up_base < 0.6 else "UPSTREAM_PRODUCT_CHANGE"
            if sim_up_base < 0.35 and sim_up_acc < 0.35:
                drift = "UPSTREAM_README_REWRITE"
            dnotes.append(
                f"sim(upstream,base)={sim_up_base:.3f} "
                f"sim(upstream,accepted)={sim_up_acc:.3f} "
                "(offline proxy; production uses qwen3-embedding-8b, L4)"
            )
        elif upstream_changed:
            drift = "UPSTREAM_PRODUCT_CHANGE"
        elif spans_lost:
            drift = "PRESENTATION_REGRESSION"
    else:
        drift = "MISSING_STATE"
        dnotes.append("First run: no accepted state; establishing baseline")

    # 5. PLAN + CANDIDATE — recompile desired state from current-upstream + Facts + Policy
    if drift == "COMMUNITY_FILE_DRIFT":
        restored = state["accepted_files"]["CONTRIBUTING.md"]
        cand_dir = work_root / "candidate"
        cand_dir.mkdir(parents=True, exist_ok=True)
        (cand_dir / "CONTRIBUTING.md").write_text(restored, encoding="utf-8")
        patch = "".join(
            difflib.unified_diff(
                [], restored.splitlines(keepends=True), "a/CONTRIBUTING.md", "b/CONTRIBUTING.md"
            )
        )
        (work_root / "contributing-restore.patch").write_text(patch, encoding="utf-8")
        new_state = dict(state)
        new_state["last_drift"] = drift
        store.save(state_key, new_state)
        return Result(
            status="PROPOSED",
            drift=drift,
            llm=counters,
            checks={
                "readme_untouched": True,
                "unrelated_files_untouched": True,
                "llm_calls_this_run": 0,
            },
            candidate_path=str(cand_dir / "CONTRIBUTING.md"),
            patch_path=str(work_root / "contributing-restore.patch"),
            notes=dnotes
            + [
                "Restore proposed as a patch (never silently applied; "
                "product agent may reject via response loop)."
            ],
        )

    gaps = detect_gaps(upstream, detected_license=facts.get("license"))
    paragraph = None
    if not gaps.fully_compliant and gaps.relationship_explained is False:
        paragraph = relationship_paragraph(
            facts, policy, state, fingerprint, live_llm, fixture_llm, counters
        )
    candidate = (
        upstream
        if gaps.fully_compliant
        else (
            upstream.rstrip("\n")
            + "\n\n"
            + render_resources_span(gaps, policy, paragraph, fingerprint)
            + "\n"
        )
    )

    # 6. VALIDATED — deterministic checks incl. stale-claim prevention
    stale_leaks = []
    if accepted:
        for cap in claimed_capabilities(accepted):
            if cap not in claimed and not any(k in cap.lower() for k in known):
                if cap in candidate:
                    stale_leaks.append(cap)
    import re as _re

    tail = candidate[len(upstream) :] if candidate != upstream else ""
    linked = _re.findall(r"\]\((https?://[^)]+)\)", tail)
    wl = policy.block.link_whitelist_domains
    bad_links = [u for u in linked if not any(d in u for d in wl)]
    prohibited = [t for t in policy.block.prohibited_terms if t.lower() in tail.lower()]

    # INDEPENDENT preservation proof (non-tautological): every upstream-only token must
    # appear in the candidate. These tokens exist in current-upstream but NOT in
    # base/accepted, so their presence proves the candidate was built from FRESH
    # upstream, not stale state.
    missing_new_tokens = [t for t in (new_tokens or []) if t not in candidate]
    checks = {
        "stale_claims_reintroduced": stale_leaks,
        "non_whitelisted_links": bad_links,
        "prohibited_terms": prohibited,
        # honestly labelled: this reconciliation strategy is append-only, so this
        # property holds by construction and is NOT the preservation proof.
        "candidate_is_append_only_superset_of_upstream": candidate.startswith(upstream.rstrip("\n"))
        or candidate == upstream,
        # the REAL preservation proof — fails if any fresh-upstream token was lost:
        "upstream_new_tokens_checked": new_tokens or [],
        "upstream_new_tokens_missing": missing_new_tokens,
        "llm_calls_this_run": counters["llm_calls_live"] + counters["llm_calls_fixture"],
    }
    if stale_leaks or bad_links or prohibited or missing_new_tokens:
        return Result(
            status="BLOCKED_VALIDATION_FAILED",
            drift=drift,
            llm=counters,
            checks=checks,
            notes=dnotes,
        )

    # 7. CONCURRENCY — compare-and-swap on upstream HEAD before apply
    if head_advancer:
        head_advancer()
    if git_head(source_repo) != head:
        return Result(
            status="STALE_INPUT",
            drift=drift,
            llm=counters,
            checks=checks,
            notes=dnotes
            + [
                "Upstream HEAD moved between snapshot and apply; "
                "no apply; restart required from the new revision."
            ],
        )

    # 8. APPLY (never-push) + ACCEPT
    work_root.mkdir(parents=True, exist_ok=True)
    (work_root / "README.md").write_text(candidate, encoding="utf-8")
    patch = "".join(
        difflib.unified_diff(
            upstream.splitlines(keepends=True),
            candidate.splitlines(keepends=True),
            "a/README.md",
            "b/README.md",
        )
    )
    (work_root / "readme-candidate.patch").write_text(patch, encoding="utf-8")
    store.save(
        state_key,
        {
            "schema": "RepositoryPresentationStateV1-prototype",
            "fingerprint": fingerprint,
            "upstream_commit": head,
            "upstream_base": upstream,
            "accepted_output": candidate,
            "accepted_files": {k: v for k, v in upstream_files.items() if v is not None},
            "facts_hash": facts_hash,
            "policy_hash": policy_hash,
            "tool_version": TOOL_VERSION,
            "generation_cache": {"fingerprint": fingerprint, "paragraph": paragraph}
            if paragraph
            else {},
            "last_drift": drift,
        },
    )
    return Result(
        status="PROPOSED" if drift != "MISSING_STATE" else "ACCEPTED_BASELINE",
        drift=drift,
        llm=counters,
        checks=checks,
        candidate_path=str(work_root / "README.md"),
        patch_path=str(work_root / "readme-candidate.patch"),
        notes=dnotes,
    )
