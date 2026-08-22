"""Install the bounded candidate-first portfolio campaign into the sole mission graph."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "plans/investigations/control/level8-autonomous-mission-task-graph.yaml"
DEFERRED = ROOT / "plans/investigations/control/level8-deferred-task-catalog.jsonl"
REQUIREMENTS = ROOT / "plans/requirements/catalog.jsonl"
DECISIONS = ROOT / "plans/decisions/catalog.jsonl"
MIGRATION = ROOT / "plans/investigations/evidence/agile-authority-reset-v1/migration-matrix.json"

MISSION_ID = "LEVEL8-CENTRAL-REPOSITORY-PRESENTATION"
BASELINE_REVISION = "df864ffd189167ef7e3cd458fb092c704769babe"
REGISTRY_SHA256 = "eb526af1d1c70b700a89e4445d399e1131170e5ecfb7359147bc671be6da8479"
PORTFOLIO_TASK = "L8-PORT-01-LOCAL-README-PORTFOLIO-ASPOSE-PARITY"
POST_PORTFOLIO_TASKS = {
    "L8-FRESH-00-FRESHNESS-SERVICE",
    "L8-HORIZON-01-ACTIVATE-GATE-A",
    "L8-VNET-01-ACCELERATED-LOCAL-NO-OP",
    "L8-VNET-02-PRODUCTION-TRANSPORT",
    "L8-VPY-04-PRODUCTION-TRANSPORT",
    "L8-VPY-05-PRODUCTION-ADMISSION",
}


def _focus(
    goal_id: str,
    outcome: str,
    scope: list[str],
    change_classes: list[str],
    next_goal: str,
) -> dict:
    return {
        "goal_id": goal_id,
        "immediate_outcome": outcome,
        "repository_scope": scope,
        "allowed_change_classes": change_classes,
        "next_goal_on_success": next_goal,
        "defer_nonblocking_findings": True,
        "show_output_before_broad_regression": True,
        "max_equivalent_ineffective_attempts": 2,
        "max_minutes_without_narrowing": 15,
    }


def _task(
    task_id: str,
    *,
    title: str,
    objective: str,
    why: str,
    dependencies: list[str],
    outputs: list[str],
    checks: list[str],
    verification: list[str],
    negative: list[str],
    evidence: list[str],
    goal_ids: list[str],
    contribution: str,
    focus: dict,
    allowed_paths: list[str],
    priority: str = "P0",
    lane: str = "portfolio-proof",
    parent: str | None = PORTFOLIO_TASK,
    execution_kind: str = "acceptance",
    infrastructure_admission: dict | None = None,
) -> dict:
    task = {
        "task_id": task_id,
        "mission_id": MISSION_ID,
        "parent_task_id": parent,
        "title": title,
        "source_audit_finding": (
            "The 2026-08-20 owner audit and the operator-supplied acceleration plan show that "
            "delivery stalled because machinery was generalized before one complete candidate "
            "transaction proved knowledge use, candidate quality, and immediate no-op behavior."
        ),
        "audit_classification": "final_outcome_blocker",
        "priority": priority,
        "lane": lane,
        "owner": "readme-agent-supervisor",
        "status": "TODO",
        "objective": objective,
        "why_it_matters": why,
        "allowed_paths": allowed_paths,
        "forbidden_paths": [
            "D:/onedrive/Documents/GitHub/aspose.org (read-only development oracle)",
            "production target repository remotes",
            "target default branches",
        ],
        "dependencies": dependencies,
        "expected_outputs": outputs,
        "acceptance_checks": checks,
        "verification": verification,
        "negative_controls": negative,
        "regression_checks": [
            "allow-list and push-blocking safety",
            "candidate dependency fingerprints and no-op invalidation",
            "mission graph load, dependency ordering, and durable claim recovery",
        ],
        "evidence_requirements": evidence,
        "rollback_or_recovery": (
            "Resume from the last checksum-valid stage; revert only the specific coherent control-"
            "repository commit if a regression is proven. Never reset, clean, or mutate a product remote."
        ),
        "failure_reroute": (
            "After two equivalent ineffective attempts or fifteen minutes without narrowing, stop "
            "repeating the tactic, identify the first failing causal owner, and repair or reroute it "
            "inside this graph without lowering acceptance."
        ),
        "closeout_rules": [
            "All stated outputs and negative controls have current, checksum-bound evidence.",
            "Focused and impact-mapped regression proof pass on the same committed revision.",
            "A report, schema, candidate file, or mocked test alone cannot close the task.",
        ],
        "goal_ids": goal_ids,
        "core_contribution": {"kind": "first_boundary_removal", "summary": contribution},
        "execution_kind": execution_kind,
        "execution_focus": focus,
        "requirement_ids": [],
    }
    if infrastructure_admission is not None:
        task["infrastructure_admission"] = infrastructure_admission
    return task


def _tasks() -> list[dict]:
    shared_paths = [
        "src/readme_agent/",
        "tests/",
        "plans/investigations/evidence/portfolio-proof-*",
        "plans/investigations/owner_audit/",
        "docs/",
        "logs/",
    ]
    return [
        _task(
            "L8-PF-00-CAMPAIGN-AUTHORITY-RECONCILIATION",
            title="Reconcile the 31-of-31 portfolio proof authority",
            objective=(
                "Freeze the current RegistryRevision baseline, typed processability partition, "
                "30-point acceptance identity, no-effect boundary, and candidate-first dependency "
                "order in the existing authority documents and sole mission graph."
            ),
            why="Execution cannot be fast or trustworthy while denominator, acceptance identity, and task order conflict.",
            dependencies=[],
            outputs=[
                "One bounded portfolio proof contract bound to the current registry bytes",
                "One graph-native queue with no competing controller or narrative cursor",
                "A checksum-verified owner-audit ingest and truthful current-status reconciliation",
            ],
            checks=[
                "The frozen baseline partitions 33 admitted repositories into 31 processable targets and two typed PSD dispositions",
                "The 30-point rubric and zero-hard-disqualifier rule are graph-bound",
                "Aspose.org is development input only and product effects are disabled",
            ],
            verification=[
                "mission schema and graph-loader tests",
                "compact-authority, requirement-coverage, plan-structure, and graph-drift checks",
                "owner-evidence manifest/hash/path verification",
            ],
            negative=[
                "No stale Python-first or 33-candidate statement can govern this campaign",
                "No narrative plan can override durable mission state",
            ],
            evidence=[
                "contract, graph hash, registry hash, authority-validation receipt, and owner-audit manifest",
            ],
            goal_ids=["GOAL-AUTONOMY", "GOAL-DELIVERY"],
            contribution="Remove campaign-identity and sequencing ambiguity before product execution.",
            focus=_focus(
                "DELIVERY-PORTFOLIO-AUTHORITY",
                "Freeze one executable 31-of-31 campaign identity and candidate-first queue.",
                ["portfolio:registry-revision"],
                ["shared_code", "mission_state"],
                "Close imported-knowledge and acceptance identity gaps for the first candidate.",
            ),
            allowed_paths=[
                "AGENTS.md",
                "plans/idea.md",
                "plans/master.md",
                "plans/GOVERNANCE.md",
                "plans/requirements.md",
                "plans/requirements/catalog.jsonl",
                "plans/decisions/catalog.jsonl",
                "plans/investigations/control/",
                "plans/investigations/evidence/agile-authority-reset-v1/",
                "plans/investigations/owner_audit/",
                "scripts/governance/",
                "scripts/retrofits/",
                "src/readme_agent/supervisor/",
                "tests/unit/test_mission_control.py",
                "docs/",
                "logs/",
            ],
            lane="portfolio-proof-authority",
            parent=None,
        ),
        _task(
            "L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY",
            title="Close portfolio knowledge and acceptance identity gaps",
            objective=(
                "Make repository-derived and imported Aspose.org knowledge safely useful across every "
                "processable product and platform: retain current item-level, "
                "polarity-aware corroboration; bind final post-render accountability; add bounded, "
                "deduplicated byte-changing consumers for feature, format-support, install, limitation, "
                "and troubleshooting fields; and bind the current check registry and 30-point reviewer identity."
            ),
            why=(
                "Loading and selecting 97,303 claims is not product knowledge use when five selected "
                "field families cannot change candidate bytes or prove where each selected item went."
            ),
            dependencies=["L8-PF-00-CAMPAIGN-AUTHORITY-RECONCILIATION"],
            outputs=[
                "Current-revision deterministic knowledge bundles and a coverage/disposition matrix "
                "for every processable registry repository",
                "A bounded portfolio refresh command that resumes, caches by source revision and "
                "generator identity, isolates repository failures, and emits no remote writes",
                "Safe byte-changing consumers for all five remaining imported-knowledge fields",
                "Final per-item rendered, preserved, or reasoned-omission knowledge dispositions",
                "A versioned current check-registry and 30-point acceptance identity",
            ],
            checks=[
                "A serial representative transaction proves the knowledge contract before disjoint "
                "repository refresh workers fan out across the portfolio",
                "Every processable Python, .NET, Java, C++, TypeScript, Rust, and Go repository has a "
                "current knowledge disposition; absence is explicit and does not become invented prose",
                "A current-source contradiction or stub cannot authorize a positive capability/format claim",
                "One verified item cannot promote an unverified sibling",
                "Every selected imported claim either binds exact candidate spans or a typed omission reason",
                "Changing an applicable accepted knowledge item changes useful bytes or an explicit disposition",
            ],
            verification=[
                "focused knowledge selector, evidence-polarity, knowledge-accountability, renderer, and acceptance tests",
                "real Aspose.3D Python knowledge-to-bytes proof against the immutable source revision, "
                "followed by bounded full-portfolio regeneration and heterogeneous samples",
                "negative controls for stubs, stale claims, duplicates, cap changes, and missing final accountability",
            ],
            negative=[
                "Facts or prompt packets without visible output lineage cannot satisfy knowledge use",
                "The old 103-check count cannot override the current 89-function vendored registry",
                "Accepted knowledge cannot become unbounded prose or cross-product contamination",
            ],
            evidence=[
                "per-field fact-to-output matrix, final knowledge-application artifact, current check-registry hash, and focused receipts",
            ],
            goal_ids=["GOAL-TRUTH", "GOAL-README", "GOAL-DELIVERY"],
            contribution="Turn the imported corpus from mostly logged context into safe, accountable README value.",
            focus=_focus(
                "DELIVERY-KNOWLEDGE-TO-BYTES",
                "Prove one serial knowledge transaction, then refresh and qualify knowledge for every "
                "processable registry repository while closing the five remaining consumers.",
                ["portfolio:all-processable", "aspose-3d-foss/Aspose.3D-FOSS-for-Python"],
                ["shared_code", "factuality", "presentation"],
                "Compose one complete weak-input candidate through the proven native seam.",
            ),
            allowed_paths=shared_paths,
            lane="knowledge-acceptance",
        ),
        _task(
            "L8-PF-02-COMPLETE-CANDIDATE-SEAM",
            title="Wire one complete weak-input candidate",
            objective=(
                "Run Aspose.3D FOSS for Python through the existing supervisor from immutable snapshot "
                "and verified facts to a complete, repository-specific candidate, source-content disposition "
                "ledger, claim map, patch, deterministic checks, and bounded editorial review inputs."
            ),
            why="One complete candidate reveals the real transaction boundary faster than more general orchestration work.",
            dependencies=["L8-PF-01-KNOWLEDGE-ACCEPTANCE-IDENTITY"],
            outputs=[
                "One current complete Aspose.3D Python candidate and native patch",
                "Complete source-unit, claim, knowledge, and component provenance",
                "Bounded structured author/reviewer records with no giant whole-repository prompt",
            ],
            checks=[
                "The candidate is product-specific, professional, non-promotional-first, and free of internal process narration",
                "Every material source unit and final claim has exactly one accepted disposition",
                "Commands, URLs, badges, code, Markdown structure, and Mermaid syntax remain deterministic",
            ],
            verification=[
                "focused composition/rendering/reconciliation tests",
                "real local_poc bounded canary through candidate generation",
                "current Aspose.org candidate comparison by obligations and information coverage, never wording",
            ],
            negative=[
                "The Aspose.org candidate is never a runtime input or copied prose source",
                "No partial section canary or historical candidate counts as the complete transaction",
            ],
            evidence=[
                "immutable input hashes, facts, plan, candidate, patch, claim/disposition maps, call ledger, and component versions",
            ],
            goal_ids=["GOAL-README", "GOAL-DELIVERY"],
            contribution="Produce the first complete current candidate through the real production seam.",
            focus=_focus(
                "DELIVERY-FIRST-COMPLETE-CANDIDATE",
                "Produce one complete current Aspose.3D Python candidate through supervise.",
                ["aspose-3d-foss/Aspose.3D-FOSS-for-Python"],
                ["repository_runtime", "factuality", "presentation"],
                "Seal the candidate at 30 of 30 and prove immediate complete-transaction no-op.",
            ),
            allowed_paths=shared_paths
            + ["runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/"],
            lane="first-complete-candidate",
            execution_kind="visible_delivery",
        ),
        _task(
            "L8-PF-03-SEALED-CANDIDATE-NO-OP",
            title="Seal the first 30-of-30 candidate and immediate no-op",
            objective=(
                "Independently validate the first current candidate against all 30 criterion-specific "
                "obligations with zero hard disqualifiers, then rerun the complete transaction unchanged "
                "and prove exact candidate reuse with zero provider calls and no duplicate artifacts or effects."
            ),
            why="This is the first honest unit of delivery and the behavior the later runner must automate.",
            dependencies=["L8-PF-02-COMPLETE-CANDIDATE-SEAM"],
            outputs=[
                "AGENT_ACCEPTED_30_OF_30 candidate-bound verdict",
                "Complete-transaction NO_OP_PROVEN receipt",
                "Checksum-complete independently reconstructed evidence inventory",
            ],
            checks=[
                "Every rubric criterion carries criterion-specific evidence and no average score hides a hard failure",
                "Author and independent reviewer contexts and identities are separate",
                "The unchanged rerun performs zero new author/reviewer calls and returns byte-identical artifacts",
            ],
            verification=[
                "30-point deterministic and independent review",
                "full transaction rerun under the same dependency key",
                "artifact corruption, source drift, prompt/route drift, validator drift, and reviewer drift controls",
            ],
            negative=[
                "Same-process renderer recomposition is not complete-transaction no-op proof",
                "An accepted review detached from the current candidate or component hashes fails closed",
            ],
            evidence=[
                "criterion matrix, reviewer records, final verdict, no-op receipt, LLM ledger, and SHA-256 inventory",
            ],
            goal_ids=["GOAL-README", "GOAL-AUTONOMY", "GOAL-DELIVERY"],
            contribution="Establish the first independently sealed unit of portfolio delivery.",
            focus=_focus(
                "DELIVERY-FIRST-SEALED-NO-OP",
                "Seal Aspose.3D Python at 30 of 30 and prove exact zero-call no-op.",
                ["aspose-3d-foss/Aspose.3D-FOSS-for-Python"],
                ["repository_runtime", "factuality", "presentation"],
                "Wrap only the proven transaction in the minimal graph runner.",
            ),
            allowed_paths=shared_paths
            + ["runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Python/"],
            lane="first-sealed-candidate",
        ),
        _task(
            "L8-PF-04-MINIMAL-GRAPH-RUNNER",
            title="Automate only the proven repository transaction",
            objective=(
                "Implement the smallest typed, allow-listed graph runner that selects and resumes existing "
                "handlers for the already-proven snapshot-to-acceptance transaction. It may not author, commit, "
                "push, or publish code/content and may not introduce arbitrary shell execution."
            ),
            why="Automation should scale a proven transaction, not hide an unstable one behind more machinery.",
            dependencies=["L8-PF-03-SEALED-CANDIDATE-NO-OP"],
            outputs=[
                "Typed action registry, predicates, checkpoint resume, and evidence-bound transitions",
                "One runner replay of the sealed candidate and its zero-call no-op",
                "Cancellation, retry, duplicate-delivery, and stale-checkpoint controls",
            ],
            checks=[
                "Only registered actions with typed inputs/outputs and declared side effects can run",
                "Durable state, leases, and terminal classification remain authoritative",
                "No product write capability is reachable in this campaign",
            ],
            verification=[
                "focused mission runner and registry tests",
                "kill/resume and duplicate/no-op integration proof",
                "push-blocking, allow-list, evidence redaction, and effect-null safety regression",
            ],
            negative=[
                "No arbitrary shell task, placeholder handler, or success-without-artifact transition",
                "No automation may create or commit its own implementation changes",
            ],
            evidence=[
                "runner action manifest, transition trace, recovery receipt, and sealed-candidate replay binding",
            ],
            goal_ids=["GOAL-AUTONOMY", "GOAL-DELIVERY"],
            contribution="Scale only behavior already proven end to end.",
            focus=_focus(
                "DELIVERY-PROVEN-TRANSACTION-RUNNER",
                "Automate the sealed transaction through typed allow-listed graph actions.",
                ["aspose-3d-foss/Aspose.3D-FOSS-for-Python"],
                ["shared_code", "mission_state", "safety"],
                "Qualify one complete current candidate per supported ecosystem.",
            ),
            allowed_paths=[
                "src/readme_agent/supervisor/",
                "src/readme_agent/capabilities/",
                "tests/unit/",
                "tests/integration/",
                "tests/security/",
                "runs/",
                "docs/architecture.md",
                "logs/",
            ],
            lane="proven-transaction-runner",
            execution_kind="infrastructure",
            infrastructure_admission={
                "trigger": "current_repository_blocker",
                "evidence_refs": [
                    "The sealed candidate transaction must be automated without duplicating its logic."
                ],
            },
        ),
        _task(
            "L8-PF-05-SEVEN-ECOSYSTEM-CANARIES",
            title="Qualify the proven transaction across seven ecosystems",
            objective=(
                "Run one processable representative from Python, .NET, Java, C++, TypeScript, Rust, and Go "
                "through the same sealed transaction, repairing only shared causal seams before portfolio fan-out."
            ),
            why="Seven bounded canaries expose ecosystem failures once without paying fleet-wide duplicate repair cost.",
            dependencies=["L8-PF-04-MINIMAL-GRAPH-RUNNER"],
            outputs=[
                "Seven complete current candidates with 30-of-30 acceptance and immediate no-op proof",
                "Shared ecosystem adapters or precise evidence-backed processability dispositions",
                "A measured safe repository-isolation and bounded-parallelism receipt",
            ],
            checks=[
                "Each canary uses only declared package routes and repository-specific source evidence",
                "No ecosystem can silently omit unsupported verification and still accept",
                "Shared repairs invalidate only affected stages and candidates",
            ],
            verification=[
                "per-ecosystem focused and real-repository transaction proof",
                "cross-product leakage, dependency, API, format, example, limitation, and Mermaid controls",
                "serial baseline followed by at most two disjoint workers only after isolation proof",
            ],
            negative=[
                "A canary cannot use an Aspose.org checkout at runtime",
                "A platform-specific patch cannot masquerade as an ecosystem-general solution",
            ],
            evidence=[
                "seven candidate bundles, acceptance/no-op receipts, isolation metrics, and shared-repair map",
            ],
            goal_ids=["GOAL-README", "GOAL-AUTONOMY", "GOAL-DELIVERY"],
            contribution="Prove the complete transaction is portable before fleet execution.",
            focus=_focus(
                "DELIVERY-SEVEN-ECOSYSTEM-CANARIES",
                "Accept and no-op-prove one current repository per supported ecosystem.",
                [
                    "platform:python",
                    "platform:net",
                    "platform:java",
                    "platform:cpp",
                    "platform:typescript",
                    "platform:rust",
                    "platform:go",
                ],
                ["repository_runtime", "factuality", "presentation"],
                "Fan the proven transaction across every processable registry repository.",
            ),
            allowed_paths=shared_paths + ["runs/readme-poc/"],
            priority="P1",
            lane="ecosystem-canaries",
            execution_kind="visible_delivery",
        ),
    ]


def _update_graph() -> None:
    graph = yaml.safe_load(GRAPH.read_text(encoding="utf-8"))
    graph["portfolio_proof_contract"] = {
        "contract_id": "ASPOSE-README-PORTFOLIO-PROOF-V1",
        "supporting_contract_path": "plans/investigations/control/portfolio-readme-proof-contract.md",
        "supporting_contract_sha256": "d043b3af793c7a0c9d91fa40c12ee0c35579002aa95afe89d2bc8fd438332054",
        "baseline_optimizer_revision": BASELINE_REVISION,
        "registry_path": "data/products.json",
        "registry_sha256": REGISTRY_SHA256,
        "denominator_policy": "dynamic_registry_revision",
        "baseline_admitted": 33,
        "baseline_processable": 31,
        "baseline_non_processable": 2,
        "delivery_numerator": "processable_repositories",
        "candidate_acceptance_state": "AGENT_ACCEPTED_30_OF_30",
        "campaign_terminal_state": "PORTFOLIO_AGENT_ACCEPTED",
        "rubric_path": "plans/investigations/owner_audit/aspose_candidate_rubric/RUBRIC_30.md",
        "rubric_sha256": "5b016891000c320218a762c0289ae44d6820636a66ab54f3410e87f12e876268",
        "required_score": 30,
        "hard_disqualifier_limit": 0,
        "processability_disposition": "NON_PROCESSABLE_NO_IMPLEMENTATION",
        "first_complete_candidate_before_runner": True,
        "model_route_is_campaign_configuration": True,
        "aspose_org_runtime_dependency_allowed": False,
        "product_effects_allowed": False,
    }
    contract = graph["autonomous_execution_contract"]
    contract["resume_strategy"] = (
        "Reload this graph and durable mission state, reconcile drift and leases, then claim the "
        "highest-priority dependency-ready task. Prove one knowledge-complete 30-of-30 candidate "
        "and immediate full-transaction no-op before automating the transaction, then qualify seven "
        "ecosystem canaries and fan out to all processable repositories."
    )
    authority = graph["mission_authority"]
    authority["mission_summary"] = (
        "Deliver the safest, repeatable, fastest complete README proof for every processable repository "
        "in the current RegistryRevision: 31 of 31 at the reviewed baseline, with two source-empty PSD "
        "repositories held as typed non-processable dispositions. Close imported-knowledge use and "
        "acceptance identity, seal one complete weak-input 30-of-30 candidate and immediate no-op, automate "
        "only that proven transaction, qualify seven ecosystems, then execute the fleet. Aspose.org remains "
        "development input only; this campaign performs no product effect."
    )
    authority["current_phase"] = (
        "Derived from durable state; candidate-first portfolio proof begins with campaign authority "
        "reconciliation and imported-knowledge-to-bytes closure."
    )
    outcomes = authority["in_scope_outcomes"]
    outcomes[:] = [
        item
        for item in outcomes
        if not item.startswith(
            (
                "DELIVERY-FIRST SHORT-TERM HORIZON:",
                "MEDIUM-TERM HORIZON:",
                "DELIVERY-FIRST VERTICAL-SLICE MILESTONES:",
            )
        )
    ]
    outcomes.insert(
        0,
        "IMMEDIATE PORTFOLIO OUTCOME: complete 31/31 processable README candidates at candidate-bound "
        "30/30 acceptance and immediate complete-transaction no-op; retain two evidence-bound "
        "NON_PROCESSABLE_NO_IMPLEMENTATION dispositions. No product effect is in scope.",
    )
    outcomes.insert(
        1,
        "CANDIDATE-FIRST ORDER: close imported-knowledge and acceptance identity, seal one weak-input "
        "candidate, then build the minimal runner, seven ecosystem canaries, and the full fleet. "
        "Do not generalize machinery before its transaction is proven.",
    )
    criteria = authority["mandatory_acceptance_criteria"]
    criteria.insert(
        0,
        "The current campaign numerator is every PROCESSABLE repository in its frozen RegistryRevision; "
        "NON_PROCESSABLE_NO_IMPLEMENTATION dispositions require immutable source/inventory evidence and "
        "a resume predicate and cannot be fabricated candidates.",
    )
    criteria.insert(
        1,
        "Imported knowledge is complete only when every selected item is current-source corroborated and "
        "has final candidate-span lineage or a typed omission reason; five remaining field consumers must "
        "change useful bytes safely before the first candidate seals.",
    )
    criteria.insert(
        2,
        "One complete 30-of-30 candidate and immediate zero-provider full-transaction no-op must precede "
        "the general runner and fleet fan-out.",
    )

    incoming = {task["task_id"]: task for task in _tasks()}
    existing = {task["task_id"]: task for task in graph["taskcards"]}
    existing.update(incoming)
    portfolio = existing[PORTFOLIO_TASK]
    portfolio.update(
        {
            "title": "Deliver every processable README at the sealed portfolio contract",
            "source_audit_finding": (
                "The 2026-08-20 owner audit establishes a 33-entry baseline with 31 processable "
                "repositories and two source-empty PSD dispositions; current-contract acceptance is zero."
            ),
            "audit_classification": "final_outcome_blocker",
            "priority": "P1",
            "objective": (
                "Execute the proven graph-native transaction across every processable repository in the "
                "frozen RegistryRevision until 31/31 are candidate-bound AGENT_ACCEPTED_30_OF_30 and "
                "immediate NO_OP_PROVEN; retain the two PSD non-processable dispositions and produce one "
                "global review package."
            ),
            "why_it_matters": "This is the tangible portfolio POC the owner can review; partial cohorts are development evidence only.",
            "dependencies": ["L8-PF-05-SEVEN-ECOSYSTEM-CANARIES"],
            "expected_outputs": [
                "Thirty-one complete current README candidates and native patches",
                "Thirty-one 30-of-30 independent acceptance records and immediate no-op receipts",
                "Two checksum-bound NON_PROCESSABLE_NO_IMPLEMENTATION dispositions",
                "One reconstructable portfolio summary and global human-review package",
            ],
            "acceptance_checks": [
                "accepted_processable == processable_denominator == 31 for the frozen baseline",
                "hard_disqualifiers == 0, system_failures == 0, and manifest_failures == 0",
                "every accepted candidate has complete source, fact, knowledge, claim, review, and no-op lineage",
                "no target repository effect occurred",
            ],
            "verification": [
                "failed-only repository repair with per-repository focused proof",
                "bounded complete non-live suite at the portfolio closure boundary",
                "independent manifest reconstruction and adversarial portfolio audit",
            ],
            "negative_controls": [
                "No typed disposition may hide an agent-fixable repository or pipeline defect",
                "No average quality score, historical candidate, or renderer-only no-op counts",
                "No product repository write or publication occurs before later human acceptance and authorization",
            ],
            "evidence_requirements": [
                "31 candidate bundles, two disposition bundles, campaign identity, portfolio summary, and checksum inventory",
            ],
            "closeout_rules": [
                "Every processable repository is AGENT_ACCEPTED_30_OF_30 and immediate NO_OP_PROVEN.",
                "Both non-processable dispositions bind immutable source evidence and a resume predicate.",
                "The Gate-A terminal state is PORTFOLIO_AGENT_ACCEPTED.",
            ],
            "execution_focus": _focus(
                "DELIVERY-README-PORTFOLIO-PROOF",
                "Reach 31-of-31 accepted and no-op-proven processable README candidates.",
                ["portfolio:processable-registry"],
                ["repository_runtime", "factuality", "presentation"],
                "Present the complete portfolio once for global human review.",
            ),
        }
    )
    horizon = existing["L8-HORIZON-01-ACTIVATE-GATE-A"]
    horizon["dependencies"] = [PORTFOLIO_TASK]
    horizon["objective"] = (
        "After the 31-of-31 portfolio reaches its agent-accepted terminal state, promote only the next "
        "global human-review and later authorized-delivery horizon from the hashed deferred catalog."
    )
    horizon["infrastructure_admission"]["evidence_refs"] = [
        "The 31-of-31 portfolio task must be CLOSED and the global review package reconstructable."
    ]

    queue = [task["task_id"] for task in _tasks()]
    graph["taskcards"] = [existing[task_id] for task_id in [*queue, PORTFOLIO_TASK]]

    deferred_records = [
        json.loads(line) for line in DEFERRED.read_text(encoding="utf-8").splitlines() if line
    ]
    deferred_by_id = {record["task"]["task_id"]: record for record in deferred_records}
    for task_id in POST_PORTFOLIO_TASKS:
        deferred_by_id[task_id] = {
            "schema_version": 1,
            "activation_group": "post-portfolio-horizon",
            "task": existing[task_id],
        }
    deferred_lines = [
        json.dumps(
            deferred_by_id[task_id], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        for task_id in sorted(deferred_by_id)
    ]
    deferred_payload = ("\n".join(deferred_lines) + "\n").encode("utf-8")
    DEFERRED.write_bytes(deferred_payload)
    graph["deferred_task_catalog"] = {
        "path": str(DEFERRED.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(deferred_payload).hexdigest(),
        "record_count": len(deferred_lines),
    }
    graph["deferred_task_index"] = [
        {
            "task_id": record["task"]["task_id"],
            "status": (
                "DEFERRED_WITH_REASON"
                if record["activation_group"] == "historical-control"
                else record["task"]["status"]
            ),
            "stage_goal_id": record["task"]["stage_goal_id"],
            "activation_group": record["activation_group"],
            "record_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
        }
        for record, line in zip(
            [deferred_by_id[task_id] for task_id in sorted(deferred_by_id)],
            deferred_lines,
            strict=True,
        )
    ]
    GRAPH.write_text(
        yaml.safe_dump(graph, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
    )


def _update_requirement(
    row: dict,
    *,
    requirement: str | None = None,
    status: str | None = None,
    evidence: str | None = None,
    traceability: str | None = None,
) -> None:
    for key, new_value, legacy_key in (
        ("requirement", requirement, "legacy_requirement"),
        ("status", status, "legacy_status"),
        ("acceptance_evidence", evidence, "legacy_acceptance_evidence"),
        ("traceability", traceability, "legacy_traceability"),
    ):
        if new_value is None or row.get(key) == new_value:
            continue
        row.setdefault(legacy_key, row.get(key))
        row[key] = new_value


def _update_requirements() -> None:
    rows = [
        json.loads(line) for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines() if line
    ]
    by_id = {row["requirement_id"]: row for row in rows}
    _update_requirement(
        by_id["L8-037"],
        requirement=(
            "Every admitted repository MUST receive one durable revision-bound processability preflight "
            "before facts, provider calls, or candidate authoring. It MUST become PROCESSABLE or a typed "
            "NON_PROCESSABLE_NO_IMPLEMENTATION disposition binding the immutable source revision, inventory, "
            "reason, evidence, zero authoring/provider work, and exact resume predicate. Agent-fixable evidence, "
            "toolchain, extraction, or validation gaps MUST remain processable work, never dispositions."
        ),
        status="PARTIAL",
        evidence=(
            "Existing intake/preflight and durable deduplication are implemented and tested, but the current "
            "runtime does not yet own the typed PROCESSABLE/NON_PROCESSABLE_NO_IMPLEMENTATION partition. The "
            "2026-08-20 owner audit independently identifies 31 substantive repositories and two source-empty "
            "PSD repositories; production wiring and negative controls remain open under L8-PF-00/01."
        ),
        traceability="Decision 84/108; L8-PF-00; L8-PF-01; PIL-015",
    )
    _update_requirement(
        by_id["L8-038"],
        requirement=(
            "RegistryRevisionV1 MUST bind discovery sources, observations, naming contract, products registry, "
            "processability dispositions, additions, renames, archives, exclusions, failures, and freshness. "
            "Every campaign MUST derive its dynamic processable denominator and typed non-processable partition "
            "from that exact revision; later discovery or admission growth reopens only affected proof."
        ),
        evidence=(
            "Revision/freshness machinery exists. The 2026-08-20 baseline audit supplies supporting evidence "
            "for 33 admitted = 31 processable + 2 non-processable, but the current graph/runtime still needs to "
            "bind that partition and reconstruct it through the production path."
        ),
        traceability="Decision 84/108; PIL-015; L8-PF-00",
    )
    _update_requirement(
        by_id["PIL-015"],
        requirement=(
            "Portfolio README proof MUST be calculated from the current complete RegistryRevisionV1. Every "
            "PROCESSABLE repository MUST have immutable source/facts, complete candidate/disposition/claim "
            "lineage, deterministic validation, independent 30-of-30 approval with zero hard disqualifiers, "
            "and immediate complete-transaction no-op proof. Typed non-processable dispositions remain outside "
            "the numerator but inside complete revision accountability."
        ),
        evidence=(
            "Current contract proof is 0/31 processable repositories. The reviewed baseline also has two "
            "source-empty PSD disposition candidates. Closure requires 31 accepted/no-op bundles, two valid "
            "disposition bundles, zero failures, and independent portfolio-manifest reconstruction."
        ),
        traceability="Decision 108; RDM-026; L8-037/038/046/048; L8-PORT-01",
    )
    _update_requirement(
        by_id["PIL-016"],
        requirement=(
            "Verified product proposal effects MAY proceed one complete platform at a time only after every "
            "current repository in that platform is repository-verified, independently accepted, fresh-"
            "transaction-no-op-proven, source-fresh, PR_ELIGIBLE, transport-qualified, and separately "
            "authorized for the exact effect. Human content acceptance is not a prerequisite. Platform "
            "publication MUST NOT promote another platform or satisfy full-registry Gate A/B."
        ),
        evidence=(
            "The readiness reducer now excludes human content review while retaining separate fresh effect "
            "authorization. Full platform transport/effect proof remains open after autonomous Gate B."
        ),
        traceability="Decisions 78/85/91/108; AUTH-008; L8-PF-07",
    )
    _update_requirement(
        by_id["L8-016"],
        requirement=(
            "The candidate campaign MUST bind a clean PlanFreezeV1, immutable PipelineContractSnapshotV1, "
            "RegistryRevisionV1, current check-registry hash, 30-point reviewer standard, prompt/model route, "
            "template components, and stage dependency manifests. It MUST first seal one current Aspose.3D "
            "Python candidate and complete-transaction no-op, then automate that transaction, qualify one "
            "representative per ecosystem, and fan out to the processable portfolio."
        ),
        evidence=(
            "Component hashing and narrow invalidation exist. The candidate-first identity is not yet sealed "
            "by one current 30-of-30 candidate/no-op transaction; L8-PF-00 through L8-PF-03 own that boundary."
        ),
        traceability="Decision 108; L8-PF-00/01/02/03; L8-042/043/046",
    )
    _update_requirement(
        by_id["L8-017"],
        requirement=(
            "Local portfolio execution MUST enforce one renewable writer lease and mission claim, terminate "
            "descendants on cancellation, and maintain one serialized campaign aggregate. The first sealed "
            "candidate MUST use one repository lane. Only after its complete lifecycle, recovery, cache, no-op, "
            "and aggregation isolation proof MAY the supervisor admit two disjoint repository workers and then "
            "a third under the measured concurrency policy. A live claim is never stolen and an expired claim "
            "remains recoverable."
        ),
        evidence=(
            "Lease and recovery primitives exist, but the candidate-first transaction has not yet supplied the "
            "required isolation baseline or bounded-parallel canary proof. L8-PF-03/04/05 own the remaining work."
        ),
        traceability="Decision 95/108; L8-PF-03/04/05; SCL-002",
    )
    _update_requirement(
        by_id["L8-046"],
        requirement=(
            "Before a general runner or portfolio fan-out, the current Aspose.3D FOSS for Python revision MUST "
            "complete one knowledge-accountable repository_verified transaction through candidate-bound 30/30 "
            "independent acceptance, zero hard disqualifiers, immediate full-transaction no-op with zero provider "
            "calls, committed promotion, and independent manifest reconstruction."
        ),
        evidence=(
            "No current candidate satisfies this complete contract. K1 item-level polarity and K3 post-render "
            "accountability now exist in code, but five C1 imported-knowledge fields still lack useful-byte "
            "consumers and the 30-point current candidate/no-op proof remains open."
        ),
        traceability="Decision 108; KNOW-003/004/013; L8-PF-01/02/03",
    )
    _update_requirement(
        by_id["L8-048"],
        requirement=(
            "Factual validity, presentation validity/version, AGENT_ACCEPTED_30_OF_30, immediate no-op, "
            "source freshness, campaign terminal state, publication eligibility, effect authorization, and "
            "effect execution MUST remain separate. Human content review is optional and MUST NOT block "
            "candidate readiness. The current campaign stops at "
            "PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION and performs no product effect."
        ),
        evidence=(
            "The aggregate reducer and per-repository transition contract now separate agent acceptance, no-op, "
            "publication readiness, and effect authority without requiring human content review. Full current "
            "31-of-31 and zero-effect publication-readiness proof remains open in the sole mission graph."
        ),
        traceability=(
            "Decision 91/108; PIL-015; L8-PF-03; L8-PORT-01; "
            "L8-PF-07-AUTONOMOUS-PUBLICATION-READINESS"
        ),
    )
    _update_requirement(
        by_id["RDM-026"],
        requirement=(
            "Every finalized verified README MUST be a stable, committed, human-reviewable control-repository "
            "artifact. The immediate campaign covers every PROCESSABLE repository in its frozen RegistryRevision, "
            "not a platform-first subset; the reviewed baseline is 31 repositories."
        ),
        evidence=(
            "Historical promoted artifacts remain useful but no repository currently satisfies the new "
            "candidate-bound 30-point acceptance identity. Closure requires 31 committed candidate bundles and "
            "two separately typed non-processable dispositions."
        ),
        traceability="Decision 108; PIL-015; L8-PORT-01",
    )
    REQUIREMENTS.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _update_decision() -> None:
    rows = [json.loads(line) for line in DECISIONS.read_text(encoding="utf-8").splitlines() if line]
    by_id = {row["decision_id"]: row for row in rows}

    amendments = {
        78: (
            "Full-registry verified local README proof uses the dynamic processable denominator.",
            "78. **Full-registry verified local README proof uses the dynamic processable denominator.** "
            "Every PROCESSABLE repository in the frozen RegistryRevision must reach candidate-bound 30/30 "
            "independent acceptance and immediate complete-transaction no-op before autonomous publication "
            "readiness. "
            "A repository with no implementation may use only a typed, evidence-bound "
            "NON_PROCESSABLE_NO_IMPLEMENTATION disposition with a resume predicate; it remains inside revision "
            "accountability but outside the delivery numerator. Partial cohorts and historical candidates are "
            "development evidence, never portfolio closure. Human content review is optional. Autonomous Gate B "
            "must make the full processable portfolio source-fresh and PR_ELIGIBLE before any separately authorized "
            "Gate-C effect. (Revised in place by Decision 108.)",
        ),
        88: (
            "Suspend trusted execution and make a sealed verified transaction the immediate critical path.",
            "88. **Suspend trusted execution and make a sealed verified transaction the immediate critical "
            "path.** Preserve compatible trusted machinery only behind verified contracts. Close imported-"
            "knowledge use and acceptance identity, then complete one current weak-input candidate at 30/30 "
            "with zero hard disqualifiers and immediate zero-provider transaction no-op. Only after that proof "
            "may the system automate the transaction, qualify ecosystem canaries, and fan out across the "
            "processable portfolio. Platform transport is later than complete autonomous portfolio publication "
            "readiness. (Revised in place by Decision 108.)",
        ),
        90: (
            "Presentation versions freeze; presentation design remains agile.",
            "90. **Presentation versions freeze; presentation design remains agile.** Each repository pins "
            "component versions for reproducibility. Later cosmetic, structural, prose-policy, fact-slot, "
            "factuality/safety, or major-document changes invalidate only their semantic dependants. A non-critical "
            "new version yields VALID_UPDATE_AVAILABLE; it does not erase factual validity, independent acceptance, "
            "or the completed numerator. Only factual, safety, protected-content, or severe acceptance defects "
            "invalidate an accepted README.",
        ),
        91: (
            "Acceptance is staged, autonomous, and multi-dimensional.",
            "91. **Acceptance is staged, autonomous, and multi-dimensional.** Facts, presentation validity/version, "
            "independent review, no-op proof, source freshness, publication eligibility, effect authorization, and "
            "effect execution are recorded independently. Human content review is optional and never blocks candidate "
            "readiness. The complete processable portfolio may become PR_ELIGIBLE only after every repository is "
            "current, independently accepted, fresh-transaction-no-op-proven, and bound to a validated effect-neutral "
            "proposal payload. No readiness state grants effect authority; every product effect still requires its "
            "own fresh exact authorization.",
        ),
        95: (
            "Adaptive parallelism begins only after one complete transaction proves isolation.",
            "95. **Adaptive parallelism begins only after one complete transaction proves isolation.** "
            "Calibration, shared repair, aggregation, transitions, commits, and closure remain serial. Once one "
            "candidate proves lifecycle, cache, cancellation, recovery, review, no-op, and aggregation isolation, "
            "the coordinator may admit two disjoint repository workers; a third is allowed only while measured "
            "speedup remains at least 1.5x and coordination overhead at or below 25 percent. Platform priority "
            "breaks ties among otherwise ready work and never creates a transport prerequisite. (Revised in place "
            "by Decision 108.)",
        ),
        98: (
            "Candidate-first portfolio sequence replaces production-admission-first platform gating.",
            "98. **Candidate-first portfolio sequence replaces production-admission-first platform gating.** "
            "Aspose.3D Python is the first weak-input transaction because it exercises rich factual and editorial "
            "risk. After it seals, one current candidate per supported ecosystem qualifies the same transaction "
            "before portfolio fan-out. Local candidates in another ecosystem do not wait for Python publication "
            "or production admission. Product effects remain later than complete autonomous portfolio publication "
            "readiness, transport qualification, and fresh exact authorization. (Revised in place by "
            "Decision 108.)",
        ),
    }
    for decision_id, (title, markdown) in amendments.items():
        row = by_id[decision_id]
        row.setdefault("legacy_title", row["title"])
        row.setdefault("legacy_markdown", row["markdown"])
        row["title"] = title
        row["markdown"] = markdown

    markdown = (
        "108. **Candidate-first graph-native portfolio proof.** The immediate campaign closes the dynamic "
        "processable denominator (31/31 at the reviewed RegistryRevision) while retaining two source-empty "
        "PSD repositories as evidence-bound NON_PROCESSABLE_NO_IMPLEMENTATION dispositions. Imported Aspose.org "
        "knowledge is a development-only corpus: current-source corroboration, post-render accountability, and "
        "useful-byte consumers must close before one weak-input candidate is sealed at 30/30 with zero hard "
        "disqualifiers and immediate complete-transaction no-op. Only then may a minimal typed allow-listed "
        "runner automate the proven transaction, followed by seven ecosystem canaries, overlapping source-complete "
        "discovery/fact warmup, and fleet fan-out. After adversarial portfolio audit, the same graph refetches "
        "sources, heals drift, derives PR_ELIGIBLE, and prepares validated effect-neutral proposal payloads. Human "
        "content review is not required. The runner never authors, commits, pushes, or publishes code/content; the "
        "campaign stops at PORTFOLIO_PUBLICATION_READY_AWAITING_EFFECT_AUTHORIZATION with no product effect. "
        "Qwen3 Next and Aspose.org comparison are versioned development inputs, not immutable mission identity "
        "or deployed runtime dependencies."
    )
    record = {
        "schema_version": 1,
        "decision_id": 108,
        "title": "Candidate-first graph-native portfolio proof.",
        "markdown": markdown,
        "legacy_record_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
    }
    by_id[108] = record
    DECISIONS.write_text(
        "\n".join(
            json.dumps(by_id[key], ensure_ascii=False, sort_keys=True) for key in sorted(by_id)
        )
        + "\n",
        encoding="utf-8",
    )


def _update_migration_matrix() -> None:
    data = json.loads(MIGRATION.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in data["new_tasks"]}
    graph = yaml.safe_load(GRAPH.read_text(encoding="utf-8"))
    for task in graph["taskcards"]:
        if not task["task_id"].startswith("L8-PF-"):
            continue
        payload = json.dumps(task, sort_keys=True, separators=(",", ":")).encode("utf-8")
        by_id[task["task_id"]] = {
            "id": task["task_id"],
            "destination": str(GRAPH.relative_to(ROOT)).replace("\\", "/"),
            "destination_task_sha256": hashlib.sha256(payload).hexdigest(),
            "reason": "candidate-first portfolio proof horizon added by Decision 108",
        }
    data["new_tasks"] = [by_id[key] for key in sorted(by_id)]
    MIGRATION.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    _update_graph()
    _update_requirements()
    _update_decision()
    _update_migration_matrix()


if __name__ == "__main__":
    main()
