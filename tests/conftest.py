"""Global test isolation for credentials and other live-only ambient state."""

import os

import pytest

_LIVE_CREDENTIAL_NAMES = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_PAT",
    "GPT_OSS_API_KEY",
    "OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def isolate_live_credentials_from_offline_tests(request, monkeypatch):
    """Offline tests never inherit credentials from a developer or CI host."""

    if request.node.get_closest_marker("live") is None:
        for name in _LIVE_CREDENTIAL_NAMES:
            monkeypatch.delenv(name, raising=False)
        # A developer's configured credential helper is also ambient authority. More
        # importantly, Git Credential Manager can survive a cancelled/finished test as an
        # orphan while waiting for interactive input. Offline tests use only local remotes,
        # so disable helpers at Git's configuration boundary instead of relying solely on
        # individual call sites to remember prompt-suppression flags.
        monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
        monkeypatch.setenv("GCM_INTERACTIVE", "never")
        # Credential helpers are multi-valued: adding a failing helper does not
        # suppress helpers inherited from system/global Git configuration. Hide
        # both ambient configuration files for offline tests. Local fixture
        # configuration remains available and every test that commits establishes
        # its own identity.
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
        # The brand-banner existence probe is a live HTTP check; offline tests
        # must compose without it. Banner-specific tests inject their own probe.
        monkeypatch.setenv("README_AGENT_BRAND_BANNER", "off")
