"""`AUTH-001`-`006` (Wave 13.2): the fail-closed authorization-record
loader, mirroring `tests/unit/test_registry_loader.py::load_policy()`'s
own tmp_path-based testing convention exactly."""

from datetime import UTC, datetime, timedelta

import pytest
import yaml
from pydantic import ValidationError

from readme_agent.authorization import registry as auth_registry
from readme_agent.authorization.schema import AuthorizationRecordV1
from readme_agent.errors import ConfigError

ORG_REPO = "acme/widget"


def _write_record(authorization_dir, **overrides) -> None:
    authorization_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "repository": ORG_REPO,
        "effect_classes": ["PR_BRANCH_PUSH", "PR_CREATE_OR_UPDATE"],
        "branch_pattern": "readme-agent/presentation-update-*",
        "allowed_surfaces": ["readme"],
        "required_validators": ["commercial_mention_discipline"],
        "required_verifier": "independent_verification",
        "approving_identity": "a-human@example.com",
        "rollback": "close the PR; nothing else to revert",
        **overrides,
    }
    (authorization_dir / "acme__widget.yml").write_text(yaml.safe_dump(record), encoding="utf-8")


class TestLoadAuthorizationRecord:
    def test_no_file_returns_none_not_an_error(self, tmp_path):
        assert auth_registry.load_authorization_record(ORG_REPO, tmp_path) is None

    def test_real_record_round_trips(self, tmp_path):
        _write_record(tmp_path)
        record = auth_registry.load_authorization_record(ORG_REPO, tmp_path)
        assert record is not None
        assert record.repository == ORG_REPO
        assert record.effect_classes == ["PR_BRANCH_PUSH", "PR_CREATE_OR_UPDATE"]
        assert record.approving_identity == "a-human@example.com"

    def test_malformed_yaml_fails_closed(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "acme__widget.yml").write_text("{not: valid: yaml:", encoding="utf-8")
        with pytest.raises(ConfigError):
            auth_registry.load_authorization_record(ORG_REPO, tmp_path)

    def test_malformed_schema_fails_closed(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "acme__widget.yml").write_text(
            yaml.safe_dump({"repository": ORG_REPO}), encoding="utf-8"
        )
        with pytest.raises(ConfigError):
            auth_registry.load_authorization_record(ORG_REPO, tmp_path)

    def test_mismatched_repository_field_fails_closed(self, tmp_path):
        """A record filed under `acme__widget.yml` but declaring a
        DIFFERENT repository must never be usable for `acme/widget` --
        this is a copy/paste hazard, not a hypothetical one."""
        _write_record(tmp_path, repository="other-org/other-repo")
        with pytest.raises(ConfigError):
            auth_registry.load_authorization_record(ORG_REPO, tmp_path)


class TestAuthorizedFor:
    def test_no_record_is_not_authorized(self, tmp_path):
        assert (
            auth_registry.authorized_for(ORG_REPO, "PR_BRANCH_PUSH", authorization_dir=tmp_path)
            is None
        )

    def test_covered_effect_class_is_authorized(self, tmp_path):
        _write_record(tmp_path)
        record = auth_registry.authorized_for(
            ORG_REPO, "PR_BRANCH_PUSH", authorization_dir=tmp_path
        )
        assert isinstance(record, AuthorizationRecordV1)

    def test_uncovered_effect_class_is_not_authorized(self, tmp_path):
        _write_record(tmp_path)
        assert (
            auth_registry.authorized_for(
                ORG_REPO, "REPOSITORY_SETTINGS_WRITE", authorization_dir=tmp_path
            )
            is None
        )

    def test_expired_record_is_not_authorized(self, tmp_path):
        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        _write_record(tmp_path, expiration=past)
        assert (
            auth_registry.authorized_for(ORG_REPO, "PR_BRANCH_PUSH", authorization_dir=tmp_path)
            is None
        )

    def test_unexpired_record_is_authorized(self, tmp_path):
        future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        _write_record(tmp_path, expiration=future)
        assert (
            auth_registry.authorized_for(ORG_REPO, "PR_BRANCH_PUSH", authorization_dir=tmp_path)
            is not None
        )

    def test_no_expiration_never_expires(self, tmp_path):
        _write_record(tmp_path, expiration=None)
        assert (
            auth_registry.authorized_for(ORG_REPO, "PR_BRANCH_PUSH", authorization_dir=tmp_path)
            is not None
        )

    def test_explicit_now_parameter_is_honored(self, tmp_path):
        expiry = datetime(2026, 1, 1, tzinfo=UTC)
        _write_record(tmp_path, expiration=expiry.isoformat())
        before = auth_registry.authorized_for(
            ORG_REPO,
            "PR_BRANCH_PUSH",
            authorization_dir=tmp_path,
            now=expiry - timedelta(seconds=1),
        )
        after = auth_registry.authorized_for(
            ORG_REPO,
            "PR_BRANCH_PUSH",
            authorization_dir=tmp_path,
            now=expiry + timedelta(seconds=1),
        )
        assert before is not None
        assert after is None


class TestAuthorizationRecordSchema:
    def test_repository_must_look_like_org_slash_repo(self):
        with pytest.raises(ValidationError):
            AuthorizationRecordV1(
                repository="not-a-valid-ref",
                effect_classes=["PR_BRANCH_PUSH"],
                branch_pattern="*",
                approving_identity="a@example.com",
                rollback="n/a",
            )

    def test_invalid_effect_class_rejected(self):
        with pytest.raises(ValidationError):
            AuthorizationRecordV1(
                repository="acme/widget",
                effect_classes=["NOT_A_REAL_EFFECT_CLASS"],
                branch_pattern="*",
                approving_identity="a@example.com",
                rollback="n/a",
            )

    def test_minimal_valid_record(self):
        record = AuthorizationRecordV1(
            repository="acme/widget",
            effect_classes=["EVIDENCE_WRITE"],
            branch_pattern="*",
            approving_identity="a@example.com",
            rollback="n/a",
        )
        assert record.allowed_surfaces == []
        assert record.expiration is None
        assert record.max_change_size is None
        assert record.required_validators == []
        assert record.required_verifier is None
