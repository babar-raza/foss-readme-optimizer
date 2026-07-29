"""Heterogeneous read-only intake through real local Git and durable lifecycle seams."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.gitsafety._git import run_git
from readme_agent.registry.models import ProductEntry
from readme_agent.state.backend import Lock, SaveResult
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.intake import run_readonly_intake_preflight


class _Backend:
    def __init__(self) -> None:
        self.states: dict[str, RunStateV2] = {}
        self.save_count = 0

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": version}
        )
        self.save_count += 1
        return SaveResult("saved", version)

    def acquire_lock(self, org_repo: str) -> Lock:
        return Lock(org_repo, "integration", "9999-01-01T00:00:00+00:00")

    def release_lock(self, lock: Lock) -> None:
        return None


def _source(root: Path, ecosystem: str, *, substantial: bool) -> Path:
    source = root / f"source-{ecosystem}"
    source.mkdir()
    run_git(["init"], cwd=source)
    run_git(["config", "user.email", "test@example.com"], cwd=source)
    run_git(["config", "user.name", "Test"], cwd=source)
    if substantial:
        readme = """# Example

Repository-specific explanation for developers.

## Installation

Use the verified source.

## Quick start

```text
example
```

## Documentation

See the [reference](https://example.invalid/reference).

## Contributing

Contributions are welcome.

## License

MIT.
""" + ("Repository evidence remains mandatory. " * 40)
    else:
        readme = f"# {ecosystem}\n\nValuable existing maintainer context.\n"
    (source / "README.md").write_text(readme, encoding="utf-8")
    run_git(["add", "."], cwd=source)
    run_git(["commit", "-m", "initial"], cwd=source)
    return source


def test_seven_ecosystems_route_once_without_any_target_effect(monkeypatch, tmp_path):
    import readme_agent.paths as path_module

    monkeypatch.setattr(path_module, "runs_dir", lambda: tmp_path / "runs")
    backend = _Backend()
    ecosystems = ("python", "net", "java", "cpp", "typescript", "rust", "go")
    first_results = []
    for index, ecosystem in enumerate(ecosystems, start=1):
        source = _source(tmp_path, ecosystem, substantial=ecosystem == "python")
        entry = ProductEntry(
            registry_schema_version=2,
            provider_identity={
                "provider": "github",
                "repository_id": index,
                "node_id": f"R_{ecosystem}",
            },
            family="example",
            platform=ecosystem,
            repo_name=f"Example-{ecosystem}",
            repo_url=f"https://github.com/example/Example-{ecosystem}",
            clone_url=str(source),
            active=True,
            discovered_via="integration",
            mode="disabled",
            ecosystem=ecosystem,
            policy_profile=f"example-{ecosystem}",
        )
        first = run_readonly_intake_preflight(entry, backend)
        saves_after_first = backend.save_count
        second = run_readonly_intake_preflight(entry, backend)
        first_results.append((entry, first))

        assert first.executed is True
        assert second.executed is False
        assert second.binding == first.binding
        assert backend.save_count == saves_after_first

    assert [result.binding.outcome for _entry, result in first_results] == [
        "READY_FAST_PATH",
        "READY_FULL_PIPELINE",
        "READY_FULL_PIPELINE",
        "READY_FULL_PIPELINE",
        "READY_FULL_PIPELINE",
        "READY_FULL_PIPELINE",
        "READY_FULL_PIPELINE",
    ]
    for entry, execution in first_results:
        receipt = json.loads(Path(execution.binding.evidence_refs[0]).read_text(encoding="utf-8"))
        assert receipt["result"]["org_repo"] == entry.org_repo
        assert receipt["result"]["target_local_effects_allowed"] is False
        assert receipt["result"]["target_remote_effects_allowed"] is False
