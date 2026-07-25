"""PRODSYS-P2-T1: tests for the warn-only verifier-wiring static check.

Uses synthetic `tmp_path` fixtures, not the real `src/readme_agent/` tree, per
`GOVERNANCE.md` rule 8's testability convention -- the real tree is exercised
directly by `run_official_checks.py` itself, not duplicated here."""

from governance.check_verifiers_are_wired import find_unwired_verifiers, main


def _write(tmp_path, relpath: str, content: str) -> None:
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestFindUnwiredVerifiers:
    def test_a_verifier_with_no_call_site_anywhere_is_flagged(self, tmp_path):
        _write(
            tmp_path,
            "verification/checker.py",
            "def verify_something(x):\n    return x\n",
        )

        unwired = find_unwired_verifiers(tmp_path)

        assert [name for name, _ in unwired] == ["verify_something"]

    def test_a_verifier_called_from_another_module_is_not_flagged(self, tmp_path):
        _write(
            tmp_path,
            "verification/checker.py",
            "def verify_something(x):\n    return x\n",
        )
        _write(
            tmp_path,
            "supervisor/loop.py",
            "from readme_agent.verification.checker import verify_something\n\n"
            "def run():\n    return verify_something(1)\n",
        )

        assert find_unwired_verifiers(tmp_path) == []

    def test_a_verifier_called_only_from_a_test_file_outside_src_root_is_still_flagged(
        self, tmp_path
    ):
        """Negative control, PRODSYS-P2-T1's own spec: 'a verifier called
        only from its own test file is correctly flagged, not silently
        passed.' `find_unwired_verifiers` only ever scans the `src_root` it's
        given (the real caller passes `src/readme_agent/`, never `tests/`),
        so a test-only call must never count as real wiring -- proven here
        by writing the "test" file outside the scanned root entirely, the
        same relationship the real src/readme_agent-vs-tests/ split has."""
        _write(
            tmp_path / "src",
            "verification/checker.py",
            "def verify_something(x):\n    return x\n",
        )
        _write(
            tmp_path / "tests",
            "test_checker.py",
            "from verification.checker import verify_something\n\n"
            "def test_it():\n    assert verify_something(1) == 1\n",
        )

        unwired = find_unwired_verifiers(tmp_path / "src")

        assert [name for name, _ in unwired] == ["verify_something"]

    def test_a_verifier_called_from_a_third_file_while_two_others_exist_is_not_flagged(
        self, tmp_path
    ):
        _write(tmp_path, "a.py", "def verify_a(x):\n    return x\n")
        _write(tmp_path, "b.py", "def verify_b(x):\n    return x\n")
        _write(tmp_path, "c.py", "from a import verify_a\ndef run():\n    return verify_a(1)\n")

        unwired = find_unwired_verifiers(tmp_path)

        assert [name for name, _ in unwired] == ["verify_b"]

    def test_no_verify_functions_returns_empty(self, tmp_path):
        _write(tmp_path, "plain.py", "def helper(x):\n    return x\n")

        assert find_unwired_verifiers(tmp_path) == []

    def test_check_mode_fails_for_an_unwired_verifier(self, tmp_path, monkeypatch):
        _write(tmp_path, "checker.py", "def verify_something(x):\n    return x\n")
        monkeypatch.setitem(main.__globals__, "SRC_ROOT", tmp_path)

        assert main(["--check"]) == 1
