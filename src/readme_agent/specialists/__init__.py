"""Wave 6+ specialists (decision #39): each module registers a
`SpecialistManifest` with `specialists/registry.py`, mirroring
`capabilities/registry.py`'s dispatch-table pattern -- adding a specialist is
a new registration, never a new call site in `supervisor/loop.py`."""
