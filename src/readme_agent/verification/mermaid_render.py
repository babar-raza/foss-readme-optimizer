"""Render Mermaid with the official CLI and validate the resulting SVG geometry."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.readme.header_visual_models import ReadmeHeaderVisualV1

MERMAID_CLI_PACKAGE = "@mermaid-js/mermaid-cli"
MERMAID_CLI_VERSION = "11.10.1"
MERMAID_RENDER_CONTRACT_VERSION = "3"
_TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)(?:[ ,]+)(-?[\d.]+)\s*\)")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MermaidNodeGeometryV1(_StrictModel):
    node_id: str
    center_x: float
    center_y: float
    width: float
    height: float


class MermaidRenderProofV1(_StrictModel):
    schema_version: int = 1
    contract_version: str = MERMAID_RENDER_CONTRACT_VERSION
    renderer: str = f"{MERMAID_CLI_PACKAGE}@{MERMAID_CLI_VERSION}"
    source_sha256: str
    svg_sha256: str
    view_box: list[float] = Field(min_length=4, max_length=4)
    aspect_ratio: float
    node_geometry: list[MermaidNodeGeometryV1]
    checks: dict[str, bool]
    errors: list[str]
    cached: bool = False
    render_duration_seconds: float

    @property
    def valid(self) -> bool:
        return bool(self.checks) and all(self.checks.values()) and not self.errors


class MermaidRenderError(RuntimeError):
    """Official Mermaid rendering or geometry validation failed closed."""


def _sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _browser_candidates() -> list[Path]:
    configured = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    candidates = [Path(configured)] if configured else []
    for command in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(Path(resolved))
    candidates.extend(
        Path(path)
        for path in (
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
    )
    return candidates


def _installed_browser() -> Path | None:
    return next((path for path in _browser_candidates() if path.is_file()), None)


def _download_browser(npx: str) -> Path:
    browser_root = paths.toolchains_dir() / "puppeteer-browsers"
    browser_root.mkdir(parents=True, exist_ok=True)
    command = [
        npx,
        "--yes",
        "@puppeteer/browsers@2.10.0",
        "install",
        "chrome@stable",
        "--path",
        str(browser_root),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=600,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-500:]
        raise MermaidRenderError(f"automatic Chrome provisioning failed: {detail}")
    names = {"chrome", "chrome.exe", "chrome-headless-shell", "chrome-headless-shell.exe"}
    installed = [path for path in browser_root.rglob("*") if path.is_file() and path.name in names]
    if not installed:
        raise MermaidRenderError("automatic Chrome provisioning produced no browser executable")
    return max(installed, key=lambda path: path.stat().st_mtime_ns)


def _official_renderer(source: str) -> bytes:
    npx = shutil.which("npx")
    if npx is None:
        raise MermaidRenderError("Node.js npx is required for official Mermaid rendering")
    browser = _installed_browser() or _download_browser(npx)
    with tempfile.TemporaryDirectory(prefix="readme-agent-mermaid-") as temp_root:
        root = Path(temp_root)
        source_path = root / "diagram.mmd"
        svg_path = root / "diagram.svg"
        source_path.write_text(source, encoding="utf-8")
        environment = {**os.environ, "PUPPETEER_EXECUTABLE_PATH": str(browser)}
        completed = subprocess.run(
            [
                npx,
                "--yes",
                f"{MERMAID_CLI_PACKAGE}@{MERMAID_CLI_VERSION}",
                "-i",
                str(source_path),
                "-o",
                str(svg_path),
            ],
            capture_output=True,
            check=False,
            env=environment,
            text=True,
            timeout=180,
        )
        if completed.returncode != 0 or not svg_path.is_file():
            detail = (completed.stderr or completed.stdout).strip()[-500:]
            raise MermaidRenderError(f"official Mermaid CLI render failed: {detail}")
        return svg_path.read_bytes()


def _view_box(root: ET.Element) -> list[float]:
    values = [float(value) for value in root.attrib.get("viewBox", "").split()]
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise MermaidRenderError("rendered Mermaid SVG has no valid viewBox")
    return values


def _node_geometries(
    root: ET.Element,
    node_ids: list[str],
) -> list[MermaidNodeGeometryV1]:
    """Recover absolute node geometry from nested flowchart subgraphs."""

    wanted = {
        re.compile(rf"(?:^|-)flowchart-{re.escape(node_id)}-\d+$"): node_id for node_id in node_ids
    }
    found: dict[str, MermaidNodeGeometryV1] = {}

    def visit(element: ET.Element, parent_x: float, parent_y: float) -> None:
        x, y = parent_x, parent_y
        if match := _TRANSLATE.fullmatch(element.attrib.get("transform", "")):
            x += float(match.group(1))
            y += float(match.group(2))
        identifier = element.attrib.get("id", "")
        node_id = next(
            (candidate for pattern, candidate in wanted.items() if pattern.search(identifier)),
            None,
        )
        if node_id is not None:
            rectangle = next(
                (
                    child
                    for child in element.iter()
                    if child.tag.endswith("rect")
                    and "label-container" in child.attrib.get("class", "")
                ),
                None,
            )
            if rectangle is not None:
                found[node_id] = MermaidNodeGeometryV1(
                    node_id=node_id,
                    center_x=x,
                    center_y=y,
                    width=float(rectangle.attrib.get("width", "0")),
                    height=float(rectangle.attrib.get("height", "0")),
                )
        for child in element:
            visit(child, x, y)

    visit(root, 0.0, 0.0)
    return [found[node_id] for node_id in node_ids if node_id in found]


def _balanced_capability_columns(nodes: list[MermaidNodeGeometryV1]) -> bool:
    if not nodes:
        return False
    columns: dict[float, list[MermaidNodeGeometryV1]] = {}
    for node in nodes:
        columns.setdefault(round(node.center_x, 1), []).append(node)
    expected_columns = 1 if len(nodes) <= 5 else 2
    if len(columns) != expected_columns:
        return False
    counts = [len(column) for column in columns.values()]
    return max(counts) - min(counts) <= 1


def _nodes_do_not_overlap(nodes: list[MermaidNodeGeometryV1]) -> bool:
    for index, left in enumerate(nodes):
        for right in nodes[index + 1 :]:
            horizontal = abs(left.center_x - right.center_x) < (left.width + right.width) / 2 - 1
            vertical = abs(left.center_y - right.center_y) < (left.height + right.height) / 2 - 1
            if horizontal and vertical:
                return False
    return True


def _peer_widths_match(nodes: list[MermaidNodeGeometryV1]) -> bool:
    if len(nodes) < 2:
        return True
    widths = [node.width for node in nodes]
    return max(widths) - min(widths) <= 1


def _required_links(root: ET.Element, visual: ReadmeHeaderVisualV1) -> bool:
    ids = {
        element.attrib.get("id", "").replace("_", "-")
        for element in root.iter()
        if element.tag.endswith("path")
    }
    inputs = [node.node_id for node in visual.diagram_nodes if node.role == "input"]
    outputs = [node.node_id for node in visual.diagram_nodes if node.role == "output"]
    required = ["-PRODUCT-CORE"]
    if inputs:
        required.append(f"-{inputs[0]}-PRODUCT")
    if outputs:
        required.append(f"-CORE-{outputs[0]}")
    return all(any(suffix in identifier for identifier in ids) for suffix in required)


def _build_proof(
    visual: ReadmeHeaderVisualV1,
    svg: bytes,
    *,
    duration: float,
    cached: bool,
) -> MermaidRenderProofV1:
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise MermaidRenderError(
            f"official Mermaid renderer returned malformed SVG: {exc}"
        ) from exc
    view_box = _view_box(root)
    expected_ids = [node.node_id for node in visual.diagram_nodes]
    geometries = _node_geometries(root, expected_ids)
    by_id = {geometry.node_id: geometry for geometry in geometries}
    capabilities = [
        by_id[node.node_id]
        for node in visual.diagram_nodes
        if node.role == "capability" and node.node_id in by_id
    ]
    inputs = [
        by_id[node.node_id]
        for node in visual.diagram_nodes
        if node.role == "input" and node.node_id in by_id
    ]
    outputs = [
        by_id[node.node_id]
        for node in visual.diagram_nodes
        if node.role == "output" and node.node_id in by_id
    ]
    aspect_ratio = view_box[2] / view_box[3]
    checks = {
        "official_renderer_succeeded": root.attrib.get("aria-roledescription") == "flowchart-v2",
        "all_semantic_nodes_rendered": set(expected_ids) == set(by_id),
        "landscape_and_compact": aspect_ratio >= 1.5 and view_box[3] <= 800,
        "capability_columns_adaptive": _balanced_capability_columns(capabilities),
        "capability_nodes_do_not_overlap": _nodes_do_not_overlap(capabilities),
        "input_peer_widths_uniform": _peer_widths_match(inputs),
        "output_peer_widths_uniform": _peer_widths_match(outputs),
        "semantic_relationship_connectors_rendered": _required_links(root, visual),
    }
    errors = [name for name, passed in checks.items() if not passed]
    return MermaidRenderProofV1(
        source_sha256=_sha256(visual.mermaid_source),
        svg_sha256=_sha256(svg),
        view_box=view_box,
        aspect_ratio=round(aspect_ratio, 4),
        node_geometry=geometries,
        checks=checks,
        errors=errors,
        cached=cached,
        render_duration_seconds=round(duration, 3),
    )


def verify_official_mermaid_render(
    visual: ReadmeHeaderVisualV1,
    *,
    renderer: Callable[[str], bytes] | None = None,
    cache_dir: Path | None = None,
) -> MermaidRenderProofV1:
    """Fail closed on Mermaid syntax or geometry the source-only gate cannot observe."""

    if not visual.mermaid_source:
        raise MermaidRenderError("official Mermaid render proof requires a diagram")
    source_hash = _sha256(visual.mermaid_source)
    resolved_cache = cache_dir or (
        paths.toolchains_dir()
        / "mermaid-render-proofs"
        / MERMAID_CLI_VERSION
        / MERMAID_RENDER_CONTRACT_VERSION
    )
    cache_path = resolved_cache / f"{source_hash}.json"
    if renderer is None and cache_path.is_file():
        cached = MermaidRenderProofV1.model_validate_json(cache_path.read_text(encoding="utf-8"))
        if cached.source_sha256 == source_hash and cached.valid:
            return cached.model_copy(update={"cached": True, "render_duration_seconds": 0.0})
    started = time.monotonic()
    svg = (renderer or _official_renderer)(visual.mermaid_source)
    proof = _build_proof(
        visual,
        svg,
        duration=time.monotonic() - started,
        cached=False,
    )
    if not proof.valid:
        raise MermaidRenderError("rendered Mermaid geometry failed: " + ", ".join(proof.errors))
    if renderer is None:
        write_redacted_json(cache_path, proof.model_dump(mode="json"))
    return proof
