"""Stable CLI handler façade over responsibility-sized modules."""

from readme_agent.commands_compatibility import (
    cmd_generate,
    cmd_inspect,
    cmd_preflight,
    cmd_profile_registry,
    cmd_report,
    cmd_run,
    cmd_run_registry,
    cmd_validate,
)
from readme_agent.commands_governance import (
    cmd_authorization_validate,
    cmd_golden_set_run,
    cmd_model_route_enable,
    cmd_scaffold_policy,
)
from readme_agent.commands_lifecycle import (
    cmd_health_report,
    cmd_recovery_sweep,
    cmd_runtime_matrix,
)
from readme_agent.commands_supervision import cmd_supervise

__all__ = [
    "cmd_authorization_validate",
    "cmd_generate",
    "cmd_golden_set_run",
    "cmd_health_report",
    "cmd_inspect",
    "cmd_model_route_enable",
    "cmd_preflight",
    "cmd_profile_registry",
    "cmd_report",
    "cmd_recovery_sweep",
    "cmd_run",
    "cmd_run_registry",
    "cmd_runtime_matrix",
    "cmd_scaffold_policy",
    "cmd_supervise",
    "cmd_validate",
]
