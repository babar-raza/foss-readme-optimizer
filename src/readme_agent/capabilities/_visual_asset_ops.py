"""Shared visual-asset helpers (Wave 8.6, item H) -- extracted out of
`prepare_visual_asset.py` so `review_visual_asset_accuracy.py` can reuse the
exact same "find an existing asset, or generate a candidate banner" logic
rather than a second, independently-drifting copy. Module-private (leading
underscore) since both callers are other capability modules within this
same package, not planner-visible surface of their own."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})
VISUAL_ASSET_SEARCH_DIRS: tuple[str, ...] = (".", ".github", "docs", "images", "assets", "img")

_MIN_DIMENSION = 16
_MAX_DIMENSION = 4096
_MAX_SIZE_BYTES = 2 * 1024 * 1024

_CANDIDATE_WIDTH = 800
_CANDIDATE_HEIGHT = 200


def find_existing_asset(baseline_path: Path) -> Path | None:
    for rel_dir in VISUAL_ASSET_SEARCH_DIRS:
        directory = baseline_path / rel_dir
        if not directory.is_dir():
            continue
        for entry in sorted(directory.iterdir()):
            if entry.is_file() and entry.suffix.lower() in IMAGE_EXTENSIONS:
                return entry
    return None


def validate_bytes(data: bytes, *, is_svg: bool) -> dict:
    concerns: list[str] = []
    size_bytes = len(data)
    if size_bytes > _MAX_SIZE_BYTES:
        concerns.append(f"file size {size_bytes} bytes exceeds {_MAX_SIZE_BYTES} byte guideline")

    if is_svg:
        return {
            "width": None,
            "height": None,
            "format": "SVG",
            "size_bytes": size_bytes,
            "size_within_reasonable_bounds": size_bytes <= _MAX_SIZE_BYTES,
            "concerns": concerns,
        }

    with Image.open(io.BytesIO(data)) as image:
        width, height = image.size
        image_format = image.format

    if width < _MIN_DIMENSION or height < _MIN_DIMENSION:
        concerns.append(f"{width}x{height} is smaller than the {_MIN_DIMENSION}px guideline")
    if width > _MAX_DIMENSION or height > _MAX_DIMENSION:
        concerns.append(f"{width}x{height} exceeds the {_MAX_DIMENSION}px guideline")

    return {
        "width": width,
        "height": height,
        "format": image_format,
        "size_bytes": size_bytes,
        "size_within_reasonable_bounds": not concerns,
        "concerns": concerns,
    }


def generate_candidate_banner(label: str) -> bytes:
    image = Image.new("RGB", (_CANDIDATE_WIDTH, _CANDIDATE_HEIGHT), color="white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    position = ((_CANDIDATE_WIDTH - text_width) // 2, (_CANDIDATE_HEIGHT - text_height) // 2)
    draw.text(position, label, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
