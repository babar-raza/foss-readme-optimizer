"""RPOC-042: unit tests for `scripts/ci/verify_local_product_example.py` --
loaded via `importlib` since `scripts/ci/` is a subdirectory, not itself on
`pythonpath` (unlike `scripts/` directly, per `pyproject.toml`), mirroring
`test_detect_template_clones.py`'s own loading convention.

Every readme_agent call this script makes (`require_listed`, `load_policy`,
`clone_baseline`, `capture_repository_snapshot`,
`verify_local_product_example`) is monkeypatched -- these tests prove the
script's own orchestration/exit-code/output-writing behavior, never real
network/build behavior (that belongs to `facts/local_verification.py`'s own
test suite, owned by the parallel RPOC-035 taskcard, not touched here)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "verify_local_product_example.py"

_spec = importlib.util.spec_from_file_location("verify_local_product_example", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
verify_local_product_example_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_local_product_example_script)


def _entry(*, policy_profile: str | None = "aspose-3d-foss") -> SimpleNamespace:
    return SimpleNamespace(
        org="aspose-3d-foss",
        repo_name="Aspose.3D-FOSS-for-Java",
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        clone_url="https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Java.git",
        policy_profile=policy_profile,
    )


def _policy(*, has_product_truth: bool = True, language: str = "java") -> SimpleNamespace:
    if not has_product_truth:
        return SimpleNamespace(product_truth=None)
    minimal_example = SimpleNamespace(language=language)
    return SimpleNamespace(product_truth=SimpleNamespace(minimal_example=minimal_example))


class _FakeResult:
    """Stands in for `LocalProductVerificationV1` without depending on its
    full schema (build/example_compile sub-models) -- only `.outcome`,
    `.detail`, and `.model_dump()` are ever used by the script under test."""

    def __init__(self, outcome: str, detail: str = "detail text") -> None:
        self.outcome = outcome
        self.detail = detail

    def model_dump(self, mode: str = "python") -> dict:
        return {"outcome": self.outcome, "detail": self.detail}


def _patch_happy_path(monkeypatch, *, result: _FakeResult, entry=None, policy=None):
    module = verify_local_product_example_script
    entry = entry or _entry()
    policy = policy if policy is not None else _policy()
    monkeypatch.setattr(module, "require_listed", lambda org_repo: entry)
    monkeypatch.setattr(module, "load_policy", lambda profile: policy)
    monkeypatch.setattr(module, "clone_baseline", lambda e, path: path)
    monkeypatch.setattr(
        module,
        "capture_repository_snapshot",
        lambda e, path: SimpleNamespace(source_revision="deadbeef"),
    )
    monkeypatch.setattr(module, "verify_local_product_example", lambda snapshot, example: result)
    return module


class TestSuccessfulVerification:
    def test_source_build_verified_exits_zero(self, monkeypatch, capsys):
        module = _patch_happy_path(monkeypatch, result=_FakeResult("SOURCE_BUILD_VERIFIED"))
        exit_code = module.main(["--org-repo", "aspose-3d-foss/Aspose.3D-FOSS-for-Java"])
        assert exit_code == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed["outcome"] == "SOURCE_BUILD_VERIFIED"

    def test_output_file_is_written_with_the_result(self, monkeypatch, tmp_path):
        module = _patch_happy_path(monkeypatch, result=_FakeResult("SOURCE_BUILD_VERIFIED"))
        output_path = tmp_path / "result.json"
        exit_code = module.main(
            [
                "--org-repo",
                "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
                "--output",
                str(output_path),
            ]
        )
        assert exit_code == 0
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written["outcome"] == "SOURCE_BUILD_VERIFIED"


class TestFailedVerification:
    def test_build_failed_exits_nonzero(self, monkeypatch):
        module = _patch_happy_path(monkeypatch, result=_FakeResult("BUILD_FAILED"))
        exit_code = module.main(["--org-repo", "aspose-3d-foss/Aspose.3D-FOSS-for-Java"])
        assert exit_code == 1

    def test_blocked_toolchain_exits_nonzero(self, monkeypatch):
        module = _patch_happy_path(monkeypatch, result=_FakeResult("BLOCKED_TOOLCHAIN"))
        exit_code = module.main(["--org-repo", "aspose-3d-foss/Aspose.3D-FOSS-for-Java"])
        assert exit_code == 1


class TestPreVerificationFailuresAreBlockedNotCrashed:
    def test_missing_policy_profile_is_blocked(self, monkeypatch, capsys):
        module = verify_local_product_example_script
        monkeypatch.setattr(module, "require_listed", lambda org_repo: _entry(policy_profile=None))
        exit_code = module.main(["--org-repo", "org/repo"])
        assert exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["outcome"] == "BLOCKED_TOOLCHAIN"
        assert "policy_profile" in payload["detail"]

    def test_missing_product_truth_is_blocked(self, monkeypatch, capsys):
        module = verify_local_product_example_script
        monkeypatch.setattr(module, "require_listed", lambda org_repo: _entry())
        monkeypatch.setattr(module, "load_policy", lambda profile: _policy(has_product_truth=False))
        exit_code = module.main(["--org-repo", "org/repo"])
        assert exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["outcome"] == "BLOCKED_TOOLCHAIN"
        assert "minimal_example" in payload["detail"]

    def test_not_allowlisted_repo_is_blocked_not_crashed(self, monkeypatch, capsys):
        module = verify_local_product_example_script

        def _raise_not_allowlisted(org_repo):
            raise module.NotAllowlistedError(f"{org_repo} is not in data/products.json")

        monkeypatch.setattr(module, "require_listed", _raise_not_allowlisted)
        exit_code = module.main(["--org-repo", "not/listed"])
        assert exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["org_repo"] == "not/listed"
        assert payload["outcome"] == "BLOCKED_TOOLCHAIN"

    def test_no_verifier_registered_for_language_is_blocked_not_crashed(self, monkeypatch, capsys):
        """The exact shape a not-yet-landed RPOC-035 ecosystem hits today:
        `verify_local_product_example()` raises a bare `ValueError` for a
        language with no registered verifier -- must be reported, never
        crash this script."""

        def _raise_no_verifier(snapshot, example):
            raise ValueError("no local example verifier registered for 'dotnet'")

        module_patched = _patch_happy_path(
            monkeypatch,
            result=_FakeResult("SOURCE_BUILD_VERIFIED"),
            policy=_policy(language="dotnet"),
        )
        monkeypatch.setattr(module_patched, "verify_local_product_example", _raise_no_verifier)
        exit_code = module_patched.main(["--org-repo", "org/repo"])
        assert exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["outcome"] == "BLOCKED_TOOLCHAIN"
        assert "no local example verifier registered" in payload["detail"]


@pytest.mark.parametrize("missing_flag", ["--org-repo"])
def test_missing_required_argument_raises_systemexit(missing_flag):
    with pytest.raises(SystemExit):
        verify_local_product_example_script.main([])
