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


class RepositorySnapshotError(GitSafetyError):
    """One logical run's immutable repository view is absent or has drifted."""


class StateBackendError(ReadmeAgentError):
    exit_code = 3


class NotAllowlistedError(ReadmeAgentError):
    exit_code = 3


class ValidationFailure(ReadmeAgentError):
    exit_code = 1


class LLMError(ReadmeAgentError):
    exit_code = 3


class LLMInfrastructureError(LLMError):
    """An external model-provider, network, or credential boundary failed."""


class MergedReviewSchemaError(LLMError):
    """The merged review response was missing/extra top-level facet keys."""


class MergedReviewRequestTooLargeError(LLMError):
    """The assembled merged-review request exceeds the pre-flight byte ceiling."""


class LLMTruncatedResponseError(LLMError):
    """A forced tool call response was cut off at finish_reason == 'length'."""

    def __init__(self, message: str, *, finish_reason: str, completion_tokens: int | None) -> None:
        super().__init__(message)
        self.finish_reason = finish_reason
        self.completion_tokens = completion_tokens
