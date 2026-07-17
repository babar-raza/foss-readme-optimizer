"""Exception hierarchy for readme_agent, mapped to CLI exit codes.

Exit codes: 0 pass, 1 validation/policy failure, 2 usage/config error,
3 preflight or git-safety failure.
"""


class ReadmeAgentError(Exception):
    exit_code = 1


class UsageError(ReadmeAgentError):
    exit_code = 2


class ConfigError(ReadmeAgentError):
    exit_code = 2


class PreflightError(ReadmeAgentError):
    exit_code = 3


class GitSafetyError(ReadmeAgentError):
    exit_code = 3


class NotAllowlistedError(ReadmeAgentError):
    exit_code = 3


class ValidationFailure(ReadmeAgentError):
    exit_code = 1


class LLMError(ReadmeAgentError):
    exit_code = 3
