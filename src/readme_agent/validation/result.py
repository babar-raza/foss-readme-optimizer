from dataclasses import dataclass
from typing import Literal

Severity = Literal["ERROR", "WARNING"]


@dataclass
class RuleResult:
    rule_name: str
    passed: bool
    severity: Severity
    message: str
