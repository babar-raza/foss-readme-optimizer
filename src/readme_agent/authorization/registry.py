"""Wave 13.2 (`AUTH-001`-`006`): fail-closed authorization-record loader,
mirroring `registry/loader.py::load_policy()`'s own shape exactly. Config
lives at `config/authorization/<org>__<repo>.yml`, sibling to (never
merged with) `config/policies/*.yml` -- the filename convention matches
`paths.py`'s own `f"{org}__{repo}"` pattern, not invented fresh.

`authorized_for()` is the single, fail-closed check Wave 13.3's real
capability wiring calls before acting -- `None` means "not authorized," in
every one of its three distinct senses (no record filed, an expired
record, a record that doesn't cover this effect class), and the caller
must produce a `CapabilityGap`/blocked finding rather than infer authority
from anything else (`AUTH-004`)."""

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import ValidationError

from readme_agent.authorization.schema import AuthorizationRecordV1, EffectClass
from readme_agent.errors import ConfigError

AUTHORIZATION_DIR = Path("config/authorization")


def _config_path(org_repo: str, authorization_dir: Path = AUTHORIZATION_DIR) -> Path:
    org, _, repo = org_repo.partition("/")
    return authorization_dir / f"{org}__{repo}.yml"


def load_authorization_record(
    org_repo: str, authorization_dir: Path = AUTHORIZATION_DIR
) -> AuthorizationRecordV1 | None:
    """`None` (never raises) when no record file exists for this repo --
    the correct, honest "not authorized yet" default: absence of a grant is
    not itself an error. Raises `ConfigError` for a record file that DOES
    exist but is malformed (invalid YAML, invalid schema, or a
    `repository` field that doesn't match `org_repo`) -- that is a real
    configuration error, never silently downgraded to "no authorization"."""
    path = _config_path(org_repo, authorization_dir)
    if not path.exists():
        return None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    try:
        record = AuthorizationRecordV1.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"{path} is malformed: {exc}") from exc
    if record.repository != org_repo:
        raise ConfigError(
            f"{path} declares repository={record.repository!r}, expected {org_repo!r} -- a "
            "record must never be usable for a repo other than the one its filename names"
        )
    return record


def _is_expired(record: AuthorizationRecordV1, *, now: datetime) -> bool:
    if record.expiration is None:
        return False
    return datetime.fromisoformat(record.expiration) <= now


def authorized_for(
    org_repo: str,
    effect_class: EffectClass,
    *,
    authorization_dir: Path = AUTHORIZATION_DIR,
    now: datetime | None = None,
) -> AuthorizationRecordV1 | None:
    """`None` means "not authorized" in any of its three senses (no record,
    an expired record, a record that doesn't cover this `effect_class`) --
    the caller must treat every one of them identically: produce a
    `CapabilityGap`/blocked finding, never infer authority from `mode ==
    "full"` or anything else (`AUTH-004`)."""
    record = load_authorization_record(org_repo, authorization_dir)
    if record is None:
        return None
    if effect_class not in record.effect_classes:
        return None
    if _is_expired(record, now=now or datetime.now(UTC)):
        return None
    return record
