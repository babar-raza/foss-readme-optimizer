"""Global test isolation for credentials and other live-only ambient state."""

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
