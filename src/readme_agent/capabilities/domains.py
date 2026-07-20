"""Registered agent-domain identifiers (`CAP-006`, Decision #33) -- the
caller-identity axis, orthogonal to `schema.py`'s `PermissionClass` blast-
radius axis. A registered set, not a closed `Literal`: the specialist list
(Wave 7) is expected to grow wave-by-wave, and a `Literal` would force a diff
to this lowest-level module every time, exactly the if/elif-chain-style churn
`AGENTS.md`'s "no monoliths" convention forbids elsewhere.

`README_RECONCILIATION` is the first real domain (Wave 6, decision #39) --
`registry.py`'s build-time checks were genuine no-ops until this entry
existed; adding exactly one domain does not itself trip the fail-closed
sunset (that needs `len(KNOWN_DOMAINS) > 1`), so no existing capability
becomes newly restricted by this addition.
"""

README_RECONCILIATION = "readme_reconciliation"

KNOWN_DOMAINS: frozenset[str] = frozenset({README_RECONCILIATION})
