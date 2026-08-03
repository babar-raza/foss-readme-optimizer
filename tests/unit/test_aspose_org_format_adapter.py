"""The Aspose.org format adapter is content-addressed and fail-closed."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from readme_agent.facts import aspose_org_format_adapter as adapter

_REVISION = "a" * 40


def _write_fake_extractor(root: Path, *, mutate_dependency: bool = False) -> Path:
    extraction = root / "scripts" / "pipeline" / "extraction"
    extraction.mkdir(parents=True)
    (extraction / "__init__.py").write_text(
        "raise RuntimeError('package initializer must not execute')\n", encoding="utf-8"
    )
    (extraction / "tree_helpers.py").write_text(
        "def get_parser(language):\n    return language\n", encoding="utf-8"
    )
    (extraction / "package_root.py").write_text(
        "def detect_package_root(root, language):\n    return root\n", encoding="utf-8"
    )
    if mutate_dependency:
        api_surface = """from pathlib import Path
def stable():
    path = Path(__file__)
    path.write_text(path.read_text(encoding='utf-8') + '\\nchanged = True\\n', encoding='utf-8')
    return True
"""
    else:
        api_surface = "def stable():\n    return True\n"
    (extraction / "api_surface.py").write_text(api_surface, encoding="utf-8")
    (extraction / "formats.py").write_text(
        """import os
from extraction.api_surface import stable
from extraction.tree_helpers import get_parser
def detect_formats(parser, language, package_root, root, family):
    assert os.environ.get('GH_TOKEN') is None
    assert sys_dont_write_bytecode()
    stable()
    return ([{'format': 'Pdf', 'direction': 'export', 'file': 'src/product.py',
              'line': 7, 'functional': True}], [])
def sys_dont_write_bytecode():
    import sys
    return sys.dont_write_bytecode
""",
        encoding="utf-8",
    )
    repository = root / "repository"
    repository.mkdir()
    return repository


def _configure(monkeypatch, root: Path) -> None:
    monkeypatch.setenv("ASPOSE_ORG_ROOT", str(root))
    monkeypatch.setenv("GH_TOKEN", "must-not-cross-boundary")
    monkeypatch.setattr(adapter, "_python", lambda _root: Path(sys.executable))
    monkeypatch.setattr(adapter, "_revision", lambda _root: _REVISION)


def test_adapter_success_hashes_exact_transitive_inputs_and_writes_no_bytecode(
    tmp_path: Path, monkeypatch
) -> None:
    repository = _write_fake_extractor(tmp_path)
    _configure(monkeypatch, tmp_path)

    result = adapter.extract_aspose_org_formats(repository, platform="python", family="note")

    assert result.status == "available"
    assert result.extractor_revision == _REVISION
    assert result.formats[0].format == "Pdf"
    assert set(result.dependency_files) == {
        "scripts/pipeline/extraction/api_surface.py",
        "scripts/pipeline/extraction/formats.py",
        "scripts/pipeline/extraction/package_root.py",
        "scripts/pipeline/extraction/tree_helpers.py",
    }
    payload = json.dumps(
        result.dependency_files,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert result.dependency_sha256 == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert (
        result.extractor_sha256 == result.dependency_files["scripts/pipeline/extraction/formats.py"]
    )
    assert not list(tmp_path.rglob("__pycache__"))
    assert len(result.receipt_sha256()) == 64


def test_adapter_reports_unavailable_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ASPOSE_ORG_ROOT", str(tmp_path / "missing"))

    result = adapter.extract_aspose_org_formats(tmp_path, platform="python", family="note")

    assert result.status == "unavailable"
    assert result.detail == "ASPOSE_ORG_ROOT is unavailable"


def test_adapter_rejects_invalid_subprocess_output(tmp_path: Path, monkeypatch) -> None:
    repository = _write_fake_extractor(tmp_path)
    _configure(monkeypatch, tmp_path)
    captured: dict[str, object] = {}

    def invalid_run(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args, 0, stdout="not-json", stderr="")

    monkeypatch.setattr(adapter.subprocess, "run", invalid_run)

    result = adapter.extract_aspose_org_formats(repository, platform="python", family="note")

    assert result.status == "unavailable"
    assert result.detail.startswith("invalid extractor output:")
    assert captured["args"][1] == "-B"
    assert captured["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert "GH_TOKEN" not in captured["env"]


def test_adapter_rejects_dependency_changed_during_execution(tmp_path: Path, monkeypatch) -> None:
    repository = _write_fake_extractor(tmp_path, mutate_dependency=True)
    _configure(monkeypatch, tmp_path)

    result = adapter.extract_aspose_org_formats(repository, platform="python", family="note")

    assert result.status == "unavailable"
    assert result.detail == (
        "extractor revision or transitive dependency bytes changed during execution"
    )
    assert result.dependency_files
    assert result.dependency_sha256


def test_adapter_reports_timeout_with_stable_provenance(tmp_path: Path, monkeypatch) -> None:
    repository = _write_fake_extractor(tmp_path)
    _configure(monkeypatch, tmp_path)

    def timed_out(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="python", timeout=120)

    monkeypatch.setattr(adapter.subprocess, "run", timed_out)

    result = adapter.extract_aspose_org_formats(repository, platform="python", family="note")

    assert result.status == "unavailable"
    assert result.detail == "Aspose.org extractor timed out"
    assert result.dependency_files
