"""Eager, fail-loud prompt registry (GOV-024, Wave 8.5) -- mirrors
capabilities/registry.py::_build()'s exact shape: every prompts/<category>/
*.yaml file is loaded and schema-validated once, keyed by its own declared
prompt_id (not filename). Prompt content itself lives only under prompts/,
never as a string literal in executable source (prompts/README.md placement
rule 9) -- this module only loads and validates it.

_build() is exposed as a plain callable (not just run-at-import) so tests can
call it directly against a fixture prompts/ tree and
monkeypatch.setattr(prompt_registry, "_MANIFESTS", ...)/"_RAW_CONTENT" the
result in -- the same self-reverting idiom capabilities/registry.py's own
tests already use (tests/unit/test_effect_ledger.py), never a manual reload()
(a bare reload() has no teardown story: monkeypatch.chdir() auto-reverts the
cwd, but a plain function call mutating module-level dicts does not
auto-revert those dicts, risking a synthetic corpus leaking into a later
test that never re-loads the real one).
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from readme_agent.errors import ConfigError
from readme_agent.llm.prompt_schema import PromptManifest
from readme_agent.readme.facts import sha256_text


def _build(
    prompts_dir: Path = Path("prompts"),
) -> tuple[dict[str, PromptManifest], dict[str, str]]:
    manifests: dict[str, PromptManifest] = {}
    raw_content: dict[str, str] = {}
    for path in sorted(prompts_dir.glob("*/*.yaml")):
        text = path.read_text(encoding="utf-8")
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
        try:
            manifest = PromptManifest.model_validate(raw)
        except ValidationError as exc:
            raise ConfigError(f"{path} is malformed: {exc}") from exc
        if manifest.category != path.parent.name:
            raise ConfigError(
                f"{path}: declared category {manifest.category!r} does not match its own "
                f"subdirectory {path.parent.name!r}"
            )
        if manifest.prompt_id in manifests:
            raise ConfigError(f"duplicate prompt_id {manifest.prompt_id!r} in prompt registry")
        manifests[manifest.prompt_id] = manifest
        raw_content[manifest.prompt_id] = text
    return manifests, raw_content


_MANIFESTS, _RAW_CONTENT = _build()


def get(prompt_id: str) -> PromptManifest | None:
    return _MANIFESTS.get(prompt_id)


def content_hash() -> str:
    """Hashes every registered prompt file, sorted by prompt_id for
    determinism -- consumed by supervisor/convergence.py::
    compute_control_plane_fingerprint(), NOT by llm/prompts.py::
    prompt_content_hash() (that one stays narrowly scoped to just
    relationship_explained, since it also feeds RepositoryFacts'
    facts-hash -- widening it here would make any unrelated prompt edit
    force every README to look stale)."""
    combined = "\x00".join(_RAW_CONTENT[key] for key in sorted(_RAW_CONTENT))
    return sha256_text(combined)
