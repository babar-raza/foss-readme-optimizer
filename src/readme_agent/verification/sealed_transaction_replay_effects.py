"""Product-effect delta proof for sealed transaction replay attestation."""

from __future__ import annotations

from typing import Any

from readme_agent.verification.sealed_transaction_replay_contracts import (
    ReplayAttestationContractV1,
)
from readme_agent.verification.sealed_transaction_replay_json import (
    _resolve_pointer,
    canonical_json_sha256,
)
from readme_agent.verification.sealed_transaction_replay_results import (
    ProductEffectDeltaV1,
    ReplayArtifactInventoryV1,
)
from readme_agent.verification.sealed_transaction_replay_vocabulary import ProductEffectV1


def _build_effect_delta(
    contract: ReplayAttestationContractV1,
    first_parsed: dict[str, Any],
    replay_parsed: dict[str, Any],
    first_inventory: ReplayArtifactInventoryV1,
    replay_inventory: ReplayArtifactInventoryV1,
) -> ProductEffectDeltaV1:
    checked: list[ProductEffectV1] = []
    proven_absent: list[ProductEffectV1] = []
    unproven: list[ProductEffectV1] = []
    violated: list[ProductEffectV1] = []

    for expectation in contract.product_effects:
        if expectation.level == "NOT_APPLICABLE":
            continue
        checked.append(expectation.effect)
        replay_document = replay_parsed.get(expectation.artifact_id)
        first_document = first_parsed.get(expectation.artifact_id)

        if expectation.comparison == "equal_across_bundles":
            first_found, first_value = (
                _resolve_pointer(first_document, expectation.json_pointer)
                if first_document is not None
                else (False, None)
            )
            replay_found, replay_value = (
                _resolve_pointer(replay_document, expectation.json_pointer)
                if replay_document is not None
                else (False, None)
            )
            if not first_found or not replay_found:
                unproven.append(expectation.effect)
            elif first_value != replay_value:
                violated.append(expectation.effect)
            else:
                proven_absent.append(expectation.effect)
        elif expectation.comparison == "equals_expected":
            document = replay_document if replay_document is not None else first_document
            found, value = (
                _resolve_pointer(document, expectation.json_pointer)
                if document is not None
                else (False, None)
            )
            if not found:
                unproven.append(expectation.effect)
            elif value != expectation.expected_value:
                violated.append(expectation.effect)
            else:
                proven_absent.append(expectation.effect)
        else:  # absent
            document = replay_document if replay_document is not None else first_document
            found, value = (
                _resolve_pointer(document, expectation.json_pointer)
                if document is not None
                else (False, None)
            )
            if found and value not in (None, [], {}, ""):
                violated.append(expectation.effect)
            else:
                proven_absent.append(expectation.effect)

    duplicate_lifecycle_paths: list[str] = []
    for directory, first_children in {
        d: set(c) for d, c in first_inventory.lifecycle_effect_children.items()
    }.items():
        replay_children = set(replay_inventory.lifecycle_effect_children.get(directory, ()))
        for child in sorted(replay_children - first_children):
            duplicate_lifecycle_paths.append(f"{directory}/{child}")
    for directory, replay_only_children in replay_inventory.lifecycle_effect_children.items():
        if directory not in first_inventory.lifecycle_effect_children:
            for child in replay_only_children:
                path = f"{directory}/{child}"
                if path not in duplicate_lifecycle_paths:
                    duplicate_lifecycle_paths.append(path)
    if duplicate_lifecycle_paths and "duplicate_lifecycle_effect" not in violated:
        if "duplicate_lifecycle_effect" in checked:
            violated.append("duplicate_lifecycle_effect")
            if "duplicate_lifecycle_effect" in proven_absent:
                proven_absent.remove("duplicate_lifecycle_effect")

    def _tree_digest(artifact_id: str, parsed: dict[str, Any], pointer: str) -> str | None:
        document = parsed.get(artifact_id)
        if document is None:
            return None
        found, value = _resolve_pointer(document, pointer)
        return value if found and isinstance(value, str) else None

    readme_write = next((e for e in contract.product_effects if e.effect == "readme_write"), None)
    tree_change = next(
        (e for e in contract.product_effects if e.effect == "target_tree_change"), None
    )
    revision_binding = next(
        (
            binding
            for binding in contract.identity_bindings
            if binding.component == "source_revision"
        ),
        None,
    )

    def _target_revision(parsed: dict[str, Any]) -> str | None:
        if revision_binding is None:
            return None
        document = parsed.get(revision_binding.artifact_id)
        if document is None:
            return None
        found, value = _resolve_pointer(document, revision_binding.json_pointer)
        return value if found and isinstance(value, str) else None

    return ProductEffectDeltaV1(
        checked_effects=tuple(sorted(set(checked))),
        proven_absent=tuple(sorted(set(proven_absent))),
        unproven=tuple(sorted(set(unproven))),
        violated=tuple(sorted(set(violated))),
        target_readme_digest_first=(
            _tree_digest(readme_write.artifact_id, first_parsed, readme_write.json_pointer)
            if readme_write is not None
            else None
        ),
        target_readme_digest_replay=(
            _tree_digest(readme_write.artifact_id, replay_parsed, readme_write.json_pointer)
            if readme_write is not None
            else None
        ),
        target_tree_digest_first=(
            _tree_digest(tree_change.artifact_id, first_parsed, tree_change.json_pointer)
            if tree_change is not None
            else None
        ),
        target_tree_digest_replay=(
            _tree_digest(tree_change.artifact_id, replay_parsed, tree_change.json_pointer)
            if tree_change is not None
            else None
        ),
        target_revision_first=_target_revision(first_parsed),
        target_revision_replay=_target_revision(replay_parsed),
        duplicate_lifecycle_paths=tuple(sorted(set(duplicate_lifecycle_paths))),
        delta_digest=canonical_json_sha256(
            {
                "proven_absent": sorted(set(proven_absent)),
                "unproven": sorted(set(unproven)),
                "violated": sorted(set(violated)),
                "duplicate": sorted(set(duplicate_lifecycle_paths)),
            }
        ),
    )
