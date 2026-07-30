"""Offline pytest sessions must not inherit or launch interactive Git authority."""

import os


def test_offline_git_credential_helpers_are_disabled():
    assert os.environ["GIT_TERMINAL_PROMPT"] == "0"
    assert os.environ["GCM_INTERACTIVE"] == "never"
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
