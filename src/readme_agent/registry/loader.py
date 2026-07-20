"""Load data/products.json + config/policies/*.yml; fail closed on malformed config.

is_permitted() is the allow-list gate for the mutating pipeline: every write
entry point calls it *before* any network/git operation. Not found, or
mode == "disabled" -> the caller raises NotAllowlistedError.

require_listed() is the separate, deliberately weaker gate for read-only
capabilities (decision #40): `mode: "disabled"` means push/full-cycle access
to that org has not been verified yet, not "excluded from analysis" -- only
presence in data/products.json is the read authorization. See
plans/master.md decision #40.
"""

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from readme_agent.errors import ConfigError, NotAllowlistedError
from readme_agent.registry.models import PolicyProfile, ProductEntry

PRODUCTS_PATH = Path("data/products.json")
POLICIES_DIR = Path("config/policies")


def load_products(products_path: Path = PRODUCTS_PATH) -> tuple[ProductEntry, ...]:
    if not products_path.exists():
        raise ConfigError(f"{products_path} not found (run from the repo root?)")
    try:
        raw = json.loads(products_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{products_path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise ConfigError(f"{products_path} must be a JSON array")
    entries = []
    for i, item in enumerate(raw):
        try:
            entries.append(ProductEntry.model_validate(item))
        except ValidationError as exc:
            raise ConfigError(f"{products_path}[{i}] is malformed: {exc}") from exc
    return tuple(entries)


def load_policy(policy_profile: str, policies_dir: Path = POLICIES_DIR) -> PolicyProfile:
    path = policies_dir / f"{policy_profile}.yml"
    if not path.exists():
        raise ConfigError(f"policy profile {policy_profile!r} not found at {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    try:
        return PolicyProfile.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{path} is malformed: {exc}") from exc


def find_entry(org_repo: str) -> ProductEntry | None:
    """org_repo is 'org/repo_name', exactly as it appears in repo_url."""
    for entry in load_products():
        if entry.org_repo == org_repo:
            return entry
    return None


def require_listed(org_repo: str) -> ProductEntry:
    """The read-only gate (decision #40): raises only if org_repo isn't in
    data/products.json at all. `mode` is irrelevant here -- it governs
    push/full-cycle readiness, never read eligibility. Use this (not
    is_permitted()/require_permitted()) for any capability whose
    side_effect_class is read_only_local/read_only_network."""
    entry = find_entry(org_repo)
    if entry is None:
        raise NotAllowlistedError(
            f"{org_repo} is not in data/products.json -- refusing to touch it. "
            "This is the hard allow-list gate."
        )
    return entry


def is_permitted(org_repo: str) -> ProductEntry | None:
    """The allow-list gate. Returns the entry only if it exists AND is enabled."""
    entry = find_entry(org_repo)
    if entry is None or entry.mode == "disabled":
        return None
    return entry


def enabled_entries() -> list[ProductEntry]:
    return [e for e in load_products() if e.mode != "disabled"]
