from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import re
from typing import Literal, cast
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from types import SimpleNamespace

from ..enums import HorizontalAlignment
from .options import PdfSaveOptions


_HYPERLINK_FIELD_RE = re.compile(r'\ufddfHYPERLINK\s+"[^"]*"')
_HYPERLINK_TARGET_RE = re.compile(r'\ufddfHYPERLINK\s+"([^"]+)"')
_LEFT_MARGIN = 40
_TOP_MARGIN = 40
_BOTTOM_MARGIN = 80
_RIGHT_MARGIN = 40
_DEFAULT_PAGE_MARGIN_POINTS = 36.0
_POINTS_PER_HALF_INCH = 36.0
_POINTS_PER_IMAGE_CM = 28.35
_DEFAULT_TAG_ICON_SIZE = 10.0
_DEFAULT_TAG_ICON_GAP = 2.0
_OUTLINE_LEVEL_INDENT = 18.0
_OUTLINE_MARKER_GAP = 6.0
_OUTLINE_MARKER_MIN_WIDTH = 12.0
_WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
_SYSTEM_FONT_ENV_VAR = "ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS"
_TAG_ICON_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".bmp")
_DEFAULT_HYPERLINK_COLOR = (0.0, 0.2, 0.65)
_COMMON_FONT_DIRS = (
    _WINDOWS_FONT_DIR,
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation2"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/opentype/noto"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
)
_FONT_VARIANTS = {
    "sans": {
        (False, False): ("Arial", "arial.ttf"),
        (True, False): ("Arial-Bold", "arialbd.ttf"),
        (False, True): ("Arial-Italic", "ariali.ttf"),
        (True, True): ("Arial-BoldItalic", "arialbi.ttf"),
    },
    "serif": {
        (False, False): ("TimesNewRoman", "times.ttf"),
        (True, False): ("TimesNewRoman-Bold", "timesbd.ttf"),
        (False, True): ("TimesNewRoman-Italic", "timesi.ttf"),
        (True, True): ("TimesNewRoman-BoldItalic", "timesbi.ttf"),
    },
    "mono": {
        (False, False): ("CourierNew", "cour.ttf"),
        (True, False): ("CourierNew-Bold", "courbd.ttf"),
        (False, True): ("CourierNew-Italic", "couri.ttf"),
        (True, True): ("CourierNew-BoldItalic", "courbi.ttf"),
    },
}
_UNICODE_FONT_CANDIDATES = {
    "sans": {
        (False, False): (("Arial", "arial.ttf"), ("DejaVuSans", "DejaVuSans.ttf"), ("LiberationSans", "LiberationSans-Regular.ttf"), ("NotoSans", "NotoSans-Regular.ttf"), ("FreeSans", "FreeSans.ttf")),
        (True, False): (("Arial-Bold", "arialbd.ttf"), ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"), ("LiberationSans-Bold", "LiberationSans-Bold.ttf"), ("NotoSans-Bold", "NotoSans-Bold.ttf"), ("FreeSans-Bold", "FreeSansBold.ttf")),
        (False, True): (("Arial-Italic", "ariali.ttf"), ("DejaVuSans-Oblique", "DejaVuSans-Oblique.ttf"), ("LiberationSans-Italic", "LiberationSans-Italic.ttf"), ("NotoSans-Italic", "NotoSans-Italic.ttf"), ("FreeSans-Oblique", "FreeSansOblique.ttf")),
        (True, True): (("Arial-BoldItalic", "arialbi.ttf"), ("DejaVuSans-BoldOblique", "DejaVuSans-BoldOblique.ttf"), ("LiberationSans-BoldItalic", "LiberationSans-BoldItalic.ttf"), ("NotoSans-BoldItalic", "NotoSans-BoldItalic.ttf"), ("FreeSans-BoldOblique", "FreeSansBoldOblique.ttf")),
    },
    "serif": {
        (False, False): (("TimesNewRoman", "times.ttf"), ("DejaVuSerif", "DejaVuSerif.ttf"), ("LiberationSerif", "LiberationSerif-Regular.ttf"), ("NotoSerif", "NotoSerif-Regular.ttf"), ("FreeSerif", "FreeSerif.ttf")),
        (True, False): (("TimesNewRoman-Bold", "timesbd.ttf"), ("DejaVuSerif-Bold", "DejaVuSerif-Bold.ttf"), ("LiberationSerif-Bold", "LiberationSerif-Bold.ttf"), ("NotoSerif-Bold", "NotoSerif-Bold.ttf"), ("FreeSerif-Bold", "FreeSerifBold.ttf")),
        (False, True): (("TimesNewRoman-Italic", "timesi.ttf"), ("DejaVuSerif-Italic", "DejaVuSerif-Italic.ttf"), ("LiberationSerif-Italic", "LiberationSerif-Italic.ttf"), ("NotoSerif-Italic", "NotoSerif-Italic.ttf"), ("FreeSerif-Italic", "FreeSerifItalic.ttf")),
        (True, True): (("TimesNewRoman-BoldItalic", "timesbi.ttf"), ("DejaVuSerif-BoldItalic", "DejaVuSerif-BoldItalic.ttf"), ("LiberationSerif-BoldItalic", "LiberationSerif-BoldItalic.ttf"), ("NotoSerif-BoldItalic", "NotoSerif-BoldItalic.ttf"), ("FreeSerif-BoldItalic", "FreeSerifBoldItalic.ttf")),
    },
    "mono": {
        (False, False): (("CourierNew", "cour.ttf"), ("DejaVuSansMono", "DejaVuSansMono.ttf"), ("LiberationMono", "LiberationMono-Regular.ttf"), ("NotoSansMono", "NotoSansMono-Regular.ttf"), ("FreeMono", "FreeMono.ttf")),
        (True, False): (("CourierNew-Bold", "courbd.ttf"), ("DejaVuSansMono-Bold", "DejaVuSansMono-Bold.ttf"), ("LiberationMono-Bold", "LiberationMono-Bold.ttf"), ("NotoSansMono-Bold", "NotoSansMono-Bold.ttf"), ("FreeMono-Bold", "FreeMonoBold.ttf")),
        (False, True): (("CourierNew-Italic", "couri.ttf"), ("DejaVuSansMono-Oblique", "DejaVuSansMono-Oblique.ttf"), ("LiberationMono-Italic", "LiberationMono-Italic.ttf"), ("NotoSansMono-Italic", "NotoSansMono-Italic.ttf"), ("FreeMono-Oblique", "FreeMonoOblique.ttf")),
        (True, True): (("CourierNew-BoldItalic", "courbi.ttf"), ("DejaVuSansMono-BoldOblique", "DejaVuSansMono-BoldOblique.ttf"), ("LiberationMono-BoldItalic", "LiberationMono-BoldItalic.ttf"), ("NotoSansMono-BoldItalic", "NotoSansMono-BoldItalic.ttf"), ("FreeMono-BoldOblique", "FreeMonoBoldOblique.ttf")),
    },
}
_BASE14_FONTS = {
    "sans": {
        (False, False): "Helvetica",
        (True, False): "Helvetica-Bold",
        (False, True): "Helvetica-Oblique",
        (True, True): "Helvetica-BoldOblique",
    },
    "serif": {
        (False, False): "Times-Roman",
        (True, False): "Times-Bold",
        (False, True): "Times-Italic",
        (True, True): "Times-BoldItalic",
    },
    "mono": {
        (False, False): "Courier",
        (True, False): "Courier-Bold",
        (False, True): "Courier-Oblique",
        (True, True): "Courier-BoldOblique",
    },
}
_REGISTERED_FONT_NAMES: dict[tuple[str, bool, bool, bool], str] = {}

_CHECKBOX_SHAPES = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 28, 30, 32, 48, 50, 52, 69, 71, 73, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99}
_STAR_SHAPES = {4, 5, 6, 13, 34, 40, 54, 61, 75}
_FLAG_SHAPES = {14, 89, 90, 91, 92, 93, 97, 98, 99}
_QUESTION_SHAPES = {15, 111}
_ARROW_RIGHT_SHAPES = {10, 11, 12, 16, 59, 80}
_ARROW_LEFT_SHAPES = {38, 58, 79}
_ARROW_UP_SHAPES = {45, 66, 86}
_ARROW_DOWN_SHAPES = {37, 57, 78}
_EXCLAMATION_SHAPES = {7, 8, 9, 17, 115}
_CONTACT_SHAPES = {18, 94, 95, 96, 114, 115, 116, 118}
_MUSIC_SHAPES = {121}
_CALENDAR_SHAPES = {19, 120, 133, 139}
_TIME_SHAPES = {20, 110, 117}
_LIGHT_SHAPES = {21, 140}
_PIN_SHAPES = {22}
_HOME_SHAPES = {23}
_COMMENT_SHAPES = {24, 111, 123}
_SMILE_SHAPES = {25}
_RIBBON_SHAPES = {26}
_KEY_SHAPES = {27}
_CHECKMARK_SHAPES = {35, 55, 76}
_MAIL_SHAPES = {106, 107, 108}
_PHONE_SHAPES = {109, 110}
_ATTACHMENT_SHAPES = {112}
_FROWN_SHAPES = {113}
_GLOBE_SHAPES = {124, 125}
_LAPTOP_SHAPES = {126}
_PLANE_SHAPES = {127}
_CAR_SHAPES = {128}
_BINOCULARS_SHAPES = {129}
_PRESENTATION_SHAPES = {130}
_LOCK_SHAPES = {131}
_BOOK_SHAPES = {132, 134, 135}
_PEN_SHAPES = {136}
_DOLLAR_SHAPES = {137, 138}
_CLOUD_SHAPES = {141}
_HEART_SHAPES = {142}
_SUN_SHAPES = {41, 62, 82, 143}


def _sanitize_text(text: str) -> str:
    return _HYPERLINK_FIELD_RE.sub("", text).replace("\ufddf", "")


def _extract_hyperlink_target(text: str) -> str | None:
    match = _HYPERLINK_TARGET_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip() or None


def _normalize_hyperlink_target(target: str | None) -> str | None:
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme:
        return target
    if "@" in target and " " not in target:
        return f"mailto:{target}"
    return f"https://{target}"


def _font_group_for_family(family_name: str) -> str:
    family_source = family_name.lower()
    if "times" in family_source or "serif" in family_source:
        return "serif"
    if any(name in family_source for name in ("courier", "consol", "mono")):
        return "mono"
    return "sans"


def _use_system_fonts() -> bool:
    value = os.environ.get(_SYSTEM_FONT_ENV_VAR, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _text_requires_unicode_font(text: str) -> bool:
    for char in text:
        codepoint = ord(char)
        if codepoint > 0x00FF:
            return True
        if 0x0400 <= codepoint <= 0x052F:
            return True
        if 0x2DE0 <= codepoint <= 0x2DFF:
            return True
        if 0xA640 <= codepoint <= 0xA69F:
            return True
    return False


def _find_font_file(group: str, bold: bool, italic: bool) -> tuple[str, Path] | None:
    candidates = _UNICODE_FONT_CANDIDATES[group][(bold, italic)]
    for alias, file_name in candidates:
        for directory in _COMMON_FONT_DIRS:
            font_path = directory / file_name
            if font_path.exists():
                return alias, font_path
    return None


def _register_font_variant(group: str, bold: bool, italic: bool, require_unicode: bool = False) -> str:
    use_system_fonts = _use_system_fonts() or require_unicode
    key = (group, bold, italic, use_system_fonts)
    if key in _REGISTERED_FONT_NAMES:
        return _REGISTERED_FONT_NAMES[key]

    if not use_system_fonts:
        name = _BASE14_FONTS[group][(bold, italic)]
        _REGISTERED_FONT_NAMES[key] = name
        return name

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        name = _BASE14_FONTS[group][(bold, italic)]
        _REGISTERED_FONT_NAMES[key] = name
        return name

    resolved = _find_font_file(group, bold, italic)
    if resolved is not None:
        alias, font_path = resolved
        if alias not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(alias, str(font_path)))
        _REGISTERED_FONT_NAMES[key] = alias
        return alias

    name = _BASE14_FONTS[group][(bold, italic)]
    _REGISTERED_FONT_NAMES[key] = name
    return name


def _font_name_for_style(style, default_font: str, text: str = "", default_bold: bool = False) -> str:
    family_source = getattr(style, "FontName", None) or default_font
    bold = bool(default_bold or getattr(style, "IsBold", getattr(style, "Bold", False)))
    italic = bool(getattr(style, "IsItalic", getattr(style, "Italic", False)))
    return _register_font_variant(_font_group_for_family(family_source), bold, italic, require_unicode=_text_requires_unicode_font(text))


def _style_bool(style, new_name: str, legacy_name: str) -> bool:
    return bool(getattr(style, new_name, getattr(style, legacy_name, False)))


def _style_value(style, new_name: str, legacy_name: str, default=None):
    return getattr(style, new_name, getattr(style, legacy_name, default))


def _tag_value(tag, new_name: str, legacy_name: str, default=None):
    return getattr(tag, new_name, getattr(tag, legacy_name, default))


def _rgb_components(color: int | None, default: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[float, float, float]:
    if color is None:
        return default
    color = max(0, min(int(color), 0xFFFFFF))
    return (color & 0xFF) / 255.0, ((color >> 8) & 0xFF) / 255.0, ((color >> 16) & 0xFF) / 255.0


def _string_width(pdf, text: str, font_name: str, font_size: float) -> float:
    if hasattr(pdf, "stringWidth"):
        return float(pdf.stringWidth(text, font_name, font_size))
    return len(text) * font_size * 0.55


def _set_fill_color(pdf, color: tuple[float, float, float]) -> None:
    if hasattr(pdf, "setFillColorRGB"):
        pdf.setFillColorRGB(*color)


def _set_stroke_color(pdf, color: tuple[float, float, float]) -> None:
    if hasattr(pdf, "setStrokeColorRGB"):
        pdf.setStrokeColorRGB(*color)


def _effective_text_color(style) -> tuple[float, float, float]:
    if getattr(style, "FontColor", None) is not None:
        return _rgb_components(getattr(style, "FontColor"))
    if getattr(style, "IsHyperlink", False) or getattr(style, "HyperlinkAddress", None):
        return _DEFAULT_HYPERLINK_COLOR
    return (0.0, 0.0, 0.0)


def _should_underline(style) -> bool:
    return bool(_style_bool(style, "IsUnderline", "Underline") or getattr(style, "IsHyperlink", False) or getattr(style, "HyperlinkAddress", None))


def _show_page(pdf, height: float) -> float:
    pdf.showPage()
    _set_fill_color(pdf, (0.0, 0.0, 0.0))
    _set_stroke_color(pdf, (0.0, 0.0, 0.0))
    return height - _TOP_MARGIN


def _fit_prefix_length(pdf, text: str, font_name: str, font_size: float, max_width: float) -> int:
    if not text:
        return 0
    if _string_width(pdf, text, font_name, font_size) <= max_width:
        return len(text)

    low = 1
    high = len(text)
    best = 0
    while low <= high:
        middle = (low + high) // 2
        if _string_width(pdf, text[:middle], font_name, font_size) <= max_width:
            best = middle
            low = middle + 1
        else:
            high = middle - 1

    if best == 0:
        return 1

    break_at = max(text.rfind(" ", 0, best), text.rfind("\t", 0, best))
    if 0 < break_at < len(text):
        return break_at + 1
    return best


def _iter_runs(rich_text):
    runs = list(getattr(rich_text, "TextRuns", getattr(rich_text, "Runs", [])) or [])
    if runs:
        return runs

    text = getattr(rich_text, "Text", "")
    if not text:
        return []

    paragraph_style = getattr(rich_text, "ParagraphStyle", None)

    fallback_style = SimpleNamespace(
        FontName=None,
        FontSize=getattr(paragraph_style, "FontSize", getattr(rich_text, "FontSize", None)),
        FontColor=getattr(paragraph_style, "FontColor", None),
        Highlight=getattr(paragraph_style, "Highlight", getattr(paragraph_style, "HighlightColor", None)),
        IsBold=_style_bool(paragraph_style, "IsBold", "Bold") if paragraph_style is not None else False,
        IsItalic=_style_bool(paragraph_style, "IsItalic", "Italic") if paragraph_style is not None else False,
        IsUnderline=_style_bool(paragraph_style, "IsUnderline", "Underline") if paragraph_style is not None else False,
        IsStrikethrough=_style_bool(paragraph_style, "IsStrikethrough", "Strikethrough") if paragraph_style is not None else False,
        IsSuperscript=_style_bool(paragraph_style, "IsSuperscript", "Superscript") if paragraph_style is not None else False,
        IsSubscript=_style_bool(paragraph_style, "IsSubscript", "Subscript") if paragraph_style is not None else False,
        HyperlinkAddress=None,
        IsHyperlink=False,
    )
    return [SimpleNamespace(Text=text, Style=fallback_style)]


def _draw_segment(pdf, x: float, y: float, text: str, style, default_font: str, default_size: float, default_bold: bool = False) -> float:
    if not text:
        return x

    font_size = max(float(getattr(style, "FontSize", None) or default_size), 1.0)
    font_name = _font_name_for_style(style, default_font, text=text, default_bold=default_bold)
    text_color = _effective_text_color(style)
    highlight = _style_value(style, "Highlight", "HighlightColor")
    baseline_shift = 0.35 * font_size if _style_bool(style, "IsSuperscript", "Superscript") else (-0.2 * font_size if _style_bool(style, "IsSubscript", "Subscript") else 0.0)
    width = _string_width(pdf, text, font_name, font_size)

    if highlight is not None and hasattr(pdf, "rect"):
        highlight_color = _rgb_components(highlight)
        _set_fill_color(pdf, highlight_color)
        pdf.rect(x, y - (font_size * 0.25) + baseline_shift, width, font_size * 1.15, stroke=0, fill=1)

    pdf.setFont(font_name, font_size)
    _set_fill_color(pdf, text_color)
    pdf.drawString(x, y + baseline_shift, text)

    if _should_underline(style) and hasattr(pdf, "line"):
        _set_stroke_color(pdf, text_color)
        pdf.line(x, y - (font_size * 0.15) + baseline_shift, x + width, y - (font_size * 0.15) + baseline_shift)
    if _style_bool(style, "IsStrikethrough", "Strikethrough") and hasattr(pdf, "line"):
        _set_stroke_color(pdf, text_color)
        pdf.line(x, y + (font_size * 0.3) + baseline_shift, x + width, y + (font_size * 0.3) + baseline_shift)

    return x + width


def _render_runs(pdf, runs, start_x: float, cursor_y: float, page_width: float, page_height: float, default_font: str = "Arial", default_size: float = 11.0, default_bold: bool = False, finish_with_newline: bool = True) -> tuple[float, float]:
    if not runs:
        return start_x, cursor_y

    x = start_x
    base_line_height = default_size * 1.35
    current_line_height = base_line_height
    rendered_any = False
    pending_hyperlink_target: str | None = None

    for run in runs:
        style = run.Style
        font_size = max(float(getattr(style, "FontSize", None) or default_size), 1.0)
        raw_text = getattr(run, "Text", "")
        font_name = _font_name_for_style(style, default_font, text=raw_text, default_bold=default_bold)
        extracted_target = _extract_hyperlink_target(raw_text)
        if extracted_target is not None:
            pending_hyperlink_target = _normalize_hyperlink_target(extracted_target)
        text = _sanitize_text(raw_text)
        run_hyperlink_target = _normalize_hyperlink_target(getattr(style, "HyperlinkAddress", None))
        if run_hyperlink_target is None and getattr(style, "IsHyperlink", False):
            run_hyperlink_target = pending_hyperlink_target
        position = 0

        while position < len(text):
            if cursor_y < _BOTTOM_MARGIN + current_line_height:
                cursor_y = _show_page(pdf, page_height)
                x = start_x
                current_line_height = base_line_height

            newline_at = text.find("\n", position)
            chunk_end = newline_at if newline_at != -1 else len(text)
            chunk = text[position:chunk_end]

            while chunk:
                current_line_height = max(current_line_height, font_size * 1.35)
                available_width = max(page_width - _RIGHT_MARGIN - x, font_size)
                piece_length = _fit_prefix_length(pdf, chunk, font_name, font_size, available_width)
                piece = chunk[:piece_length]
                if x == start_x and piece.isspace():
                    piece = ""
                    piece_length = len(chunk)
                if piece:
                    piece_start_x = x
                    x = _draw_segment(pdf, x, cursor_y, piece, style, default_font, default_size, default_bold=default_bold)
                    if run_hyperlink_target is not None and hasattr(pdf, "linkURL"):
                        pdf.linkURL(
                            run_hyperlink_target,
                            (
                                piece_start_x,
                                cursor_y - (font_size * 0.25),
                                x,
                                cursor_y + (font_size * 0.95),
                            ),
                            relative=0,
                        )
                    rendered_any = True
                chunk = chunk[piece_length:]
                if chunk:
                    cursor_y -= current_line_height
                    x = start_x
                    current_line_height = base_line_height

            if newline_at == -1:
                position = len(text)
            else:
                position = newline_at + 1
                cursor_y -= current_line_height
                x = start_x
                current_line_height = base_line_height

        if text and run_hyperlink_target is not None:
            pending_hyperlink_target = None

    if rendered_any and finish_with_newline:
        cursor_y -= current_line_height
        x = start_x
    return x, cursor_y


def _render_rich_text(pdf, rich_text, cursor_y: float, page_width: float, page_height: float, start_x: float = _LEFT_MARGIN, default_font: str = "Arial", default_size: float = 11.0, default_bold: bool = False, options: PdfSaveOptions | None = None) -> float:
    runs = _iter_runs(rich_text)
    if not runs:
        return cursor_y
    tag_offset = _render_note_tags(pdf, _tags_for_node(rich_text), start_x, cursor_y, options)
    _, cursor_y = _render_runs(pdf, runs, start_x + tag_offset, cursor_y, page_width, page_height, default_font=default_font, default_size=default_size, default_bold=default_bold)
    return cursor_y


def _render_inline_rich_texts(pdf, rich_texts, cursor_y: float, page_width: float, page_height: float, start_x: float = _LEFT_MARGIN, gap: float = 18.0, default_font: str = "Arial", default_size: float = 10.0) -> float:
    x = start_x
    rendered = False
    for rich_text in rich_texts:
        runs = _iter_runs(rich_text)
        if not runs:
            continue
        x, cursor_y = _render_runs(pdf, runs, x, cursor_y, page_width, page_height, default_font=default_font, default_size=default_size, finish_with_newline=False)
        x += gap
        rendered = True
    if rendered:
        cursor_y -= default_size * 1.6
    return cursor_y


def _normalize_tag_icon_size(options: PdfSaveOptions | None) -> float:
    return _DEFAULT_TAG_ICON_SIZE


def _normalize_tag_icon_gap(options: PdfSaveOptions | None) -> float:
    return _DEFAULT_TAG_ICON_GAP


def _normalize_tag_component(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    compact = compact.replace("/", "-").replace("\\", "-").replace(":", "-")
    return compact


def _slugify_tag_component(value: str) -> str:
    compact = _normalize_tag_component(value).lower()
    compact = re.sub(r"\s+", "-", compact)
    compact = re.sub(r"[^\w\-.]+", "", compact, flags=re.UNICODE)
    return compact.strip("-._")


def _tag_color(shape: int | None) -> tuple[float, float, float]:
    if shape in _QUESTION_SHAPES:
        return (0.64, 0.32, 0.82)
    if shape in {1, 4, 7, 10, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 96, 99, 103}:
        return (0.20, 0.58, 0.25)
    if shape in {3, 6, 9, 12, 14, 16, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 94, 97, 102, 118, 121, 124, 125, 126, 133}:
        return (0.13, 0.43, 0.82)
    if shape in {17, 98, 100, 113, 119, 137, 138, 140, 142}:
        return (0.85, 0.18, 0.16)
    return (0.92, 0.55, 0.18)


def _tag_symbol(tag) -> tuple[str, bool]:
    shape = _tag_value(tag, "Icon", "shape")
    label = _tag_value(tag, "Label", "label") or ""
    if shape in _STAR_SHAPES:
        return "★", False
    if shape in _QUESTION_SHAPES:
        return "?", False
    if shape in _EXCLAMATION_SHAPES:
        return "!", False
    if shape in _ARROW_RIGHT_SHAPES:
        return "→", False
    if shape in _ARROW_LEFT_SHAPES:
        return "←", False
    if shape in _ARROW_UP_SHAPES:
        return "↑", False
    if shape in _ARROW_DOWN_SHAPES:
        return "↓", False
    if shape in _FLAG_SHAPES:
        return "⚑", False
    if shape in _CHECKMARK_SHAPES:
        return "✓", False
    if shape in _MUSIC_SHAPES:
        return "♪", False
    if shape in _CHECKBOX_SHAPES:
        if shape in {4, 5, 6}:
            return "★", False
        if shape in {7, 8, 9}:
            return "!", False
        if shape in {10, 11, 12}:
            return "→", False
        if shape in {89, 90, 91, 92, 93, 97, 98, 99}:
            return "⚑", False
        if shape in {94, 95, 96}:
            return "P", True
        return "✓", False
    if shape in _CONTACT_SHAPES:
        return "P", True
    if shape in _CALENDAR_SHAPES:
        return "D", True
    if shape in _TIME_SHAPES:
        return "T", True
    if shape in _LIGHT_SHAPES:
        return "L", True
    if shape in _PIN_SHAPES:
        return "P", True
    if shape in _HOME_SHAPES:
        return "H", True
    if shape in _COMMENT_SHAPES:
        return "C", True
    if shape in _SMILE_SHAPES:
        return ":)", True
    if shape in _FROWN_SHAPES:
        return ":(", True
    if shape in _RIBBON_SHAPES:
        return "R", True
    if shape in _KEY_SHAPES:
        return "K", True
    if shape in _MAIL_SHAPES:
        return "M", True
    if shape in _PHONE_SHAPES:
        return "P", True
    if shape in _ATTACHMENT_SHAPES:
        return "A", True
    if shape in _GLOBE_SHAPES:
        return "G", True
    if shape in _LAPTOP_SHAPES:
        return "PC", True
    if shape in _PLANE_SHAPES:
        return "PL", True
    if shape in _CAR_SHAPES:
        return "C", True
    if shape in _BINOCULARS_SHAPES:
        return "B", True
    if shape in _PRESENTATION_SHAPES:
        return "PR", True
    if shape in _LOCK_SHAPES:
        return "L", True
    if shape in _BOOK_SHAPES:
        return "BK", True
    if shape in _PEN_SHAPES:
        return "P", True
    if shape in _DOLLAR_SHAPES:
        return "$", True
    if shape in _CLOUD_SHAPES:
        return "CL", True
    if shape in _HEART_SHAPES:
        return "H", True
    if shape in _SUN_SHAPES:
        return "S", True
    compact_label = _normalize_tag_component(label)
    if compact_label:
        return compact_label[:2], True
    return (str(shape)[:2] if shape is not None else "T"), True


def _tag_icon_candidates(tag) -> list[str]:
    shape = _tag_value(tag, "Icon", "shape")
    label = _tag_value(tag, "Label", "label") or ""
    symbol, _ = _tag_symbol(tag)
    candidates: list[str] = []
    if shape is not None:
        candidates.extend([str(shape), f"shape-{shape}"])
    compact_label = _normalize_tag_component(label)
    if compact_label:
        candidates.append(compact_label)
        slug = _slugify_tag_component(compact_label)
        if slug and slug != compact_label:
            candidates.append(slug)
    slug_symbol = _slugify_tag_component(symbol)
    if slug_symbol:
        candidates.append(slug_symbol)
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return result


def _find_tag_icon_path(tag, options: PdfSaveOptions | None) -> Path | None:
    return None


def _draw_tag_line(pdf, x1: float, y1: float, x2: float, y2: float) -> None:
    if hasattr(pdf, "line"):
        pdf.line(x1, y1, x2, y2)


def _draw_tag_rect(pdf, x: float, y: float, width: float, height: float, fill: bool = False) -> None:
    if hasattr(pdf, "rect"):
        pdf.rect(x, y, width, height, stroke=1, fill=1 if fill else 0)


def _draw_checkmark_icon(pdf, x: float, y: float, size: float) -> None:
    _draw_tag_line(pdf, x + (size * 0.18), y + (size * 0.35), x + (size * 0.40), y + (size * 0.12))
    _draw_tag_line(pdf, x + (size * 0.40), y + (size * 0.12), x + (size * 0.78), y + (size * 0.72))


def _draw_star_icon(pdf, x: float, y: float, size: float) -> None:
    points = [
        (0.50, 0.84),
        (0.62, 0.56),
        (0.90, 0.56),
        (0.68, 0.38),
        (0.76, 0.10),
        (0.50, 0.26),
        (0.24, 0.10),
        (0.32, 0.38),
        (0.10, 0.56),
        (0.38, 0.56),
    ]
    scaled = [(x + (px * size), y + (py * size)) for px, py in points]
    if hasattr(pdf, "beginPath") and hasattr(pdf, "drawPath"):
        path = pdf.beginPath()
        first_x, first_y = scaled[0]
        path.moveTo(first_x, first_y)
        for point_x, point_y in scaled[1:]:
            path.lineTo(point_x, point_y)
        path.close()
        pdf.drawPath(path, stroke=0, fill=1)
        return
    for index in range(len(scaled)):
        x1, y1 = scaled[index]
        x2, y2 = scaled[(index + 1) % len(scaled)]
        _draw_tag_line(pdf, x1, y1, x2, y2)


def _draw_arrow_icon(pdf, x: float, y: float, size: float, direction: str) -> None:
    if direction == "left":
        _draw_tag_line(pdf, x + (size * 0.78), y + (size * 0.48), x + (size * 0.22), y + (size * 0.48))
        _draw_tag_line(pdf, x + (size * 0.22), y + (size * 0.48), x + (size * 0.44), y + (size * 0.70))
        _draw_tag_line(pdf, x + (size * 0.22), y + (size * 0.48), x + (size * 0.44), y + (size * 0.26))
        return
    if direction == "up":
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.18), x + (size * 0.50), y + (size * 0.76))
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.18), x + (size * 0.28), y + (size * 0.40))
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.18), x + (size * 0.72), y + (size * 0.40))
        return
    if direction == "down":
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.18), x + (size * 0.50), y + (size * 0.76))
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.76), x + (size * 0.28), y + (size * 0.54))
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.76), x + (size * 0.72), y + (size * 0.54))
        return
    _draw_tag_line(pdf, x + (size * 0.18), y + (size * 0.48), x + (size * 0.78), y + (size * 0.48))
    _draw_tag_line(pdf, x + (size * 0.78), y + (size * 0.48), x + (size * 0.56), y + (size * 0.70))
    _draw_tag_line(pdf, x + (size * 0.78), y + (size * 0.48), x + (size * 0.56), y + (size * 0.26))


def _draw_question_icon(pdf, x: float, y: float, size: float) -> None:
    _draw_tag_line(pdf, x + (size * 0.26), y + (size * 0.66), x + (size * 0.40), y + (size * 0.82))
    _draw_tag_line(pdf, x + (size * 0.40), y + (size * 0.82), x + (size * 0.62), y + (size * 0.82))
    _draw_tag_line(pdf, x + (size * 0.62), y + (size * 0.82), x + (size * 0.74), y + (size * 0.64))
    _draw_tag_line(pdf, x + (size * 0.74), y + (size * 0.64), x + (size * 0.50), y + (size * 0.46))
    _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.46), x + (size * 0.50), y + (size * 0.28))
    _draw_tag_rect(pdf, x + (size * 0.45), y + (size * 0.08), size * 0.10, size * 0.10, fill=True)


def _draw_flag_icon(pdf, x: float, y: float, size: float) -> None:
    _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.12), x + (size * 0.24), y + (size * 0.82))
    _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.78), x + (size * 0.72), y + (size * 0.66))
    _draw_tag_line(pdf, x + (size * 0.72), y + (size * 0.66), x + (size * 0.24), y + (size * 0.52))


def _draw_contact_icon(pdf, x: float, y: float, size: float) -> None:
    if hasattr(pdf, "circle"):
        pdf.circle(x + (size * 0.50), y + (size * 0.68), size * 0.16, stroke=1, fill=0)
    else:
        _draw_tag_rect(pdf, x + (size * 0.40), y + (size * 0.58), size * 0.20, size * 0.20)
    _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.26), x + (size * 0.76), y + (size * 0.26))
    _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.26), x + (size * 0.36), y + (size * 0.44))
    _draw_tag_line(pdf, x + (size * 0.76), y + (size * 0.26), x + (size * 0.64), y + (size * 0.44))


def _draw_music_icon(pdf, x: float, y: float, size: float) -> None:
    _draw_tag_line(pdf, x + (size * 0.58), y + (size * 0.78), x + (size * 0.58), y + (size * 0.30))
    _draw_tag_line(pdf, x + (size * 0.58), y + (size * 0.78), x + (size * 0.80), y + (size * 0.72))
    _draw_tag_rect(pdf, x + (size * 0.22), y + (size * 0.10), size * 0.18, size * 0.16, fill=False)
    _draw_tag_rect(pdf, x + (size * 0.52), y + (size * 0.16), size * 0.18, size * 0.16, fill=False)


def _draw_calendar_icon(pdf, x: float, y: float, size: float) -> None:
    _draw_tag_rect(pdf, x + (size * 0.14), y + (size * 0.14), size * 0.72, size * 0.66)
    _draw_tag_line(pdf, x + (size * 0.14), y + (size * 0.62), x + (size * 0.86), y + (size * 0.62))
    _draw_tag_line(pdf, x + (size * 0.30), y + (size * 0.86), x + (size * 0.30), y + (size * 0.68))
    _draw_tag_line(pdf, x + (size * 0.70), y + (size * 0.86), x + (size * 0.70), y + (size * 0.68))


def _draw_clock_icon(pdf, x: float, y: float, size: float) -> None:
    if hasattr(pdf, "circle"):
        pdf.circle(x + (size * 0.50), y + (size * 0.50), size * 0.34, stroke=1, fill=0)
    else:
        _draw_tag_rect(pdf, x + (size * 0.18), y + (size * 0.18), size * 0.64, size * 0.64)
    _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.50), x + (size * 0.50), y + (size * 0.66))
    _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.50), x + (size * 0.64), y + (size * 0.40))


def _draw_generic_badge(pdf, x: float, y: float, size: float, shape: int | None) -> None:
    _draw_tag_rect(pdf, x + (size * 0.12), y + (size * 0.12), size * 0.76, size * 0.76)
    if shape is not None and shape % 3 == 0:
        _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.24), x + (size * 0.76), y + (size * 0.76))
    elif shape is not None and shape % 3 == 1:
        _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.50), x + (size * 0.76), y + (size * 0.50))
        _draw_tag_line(pdf, x + (size * 0.50), y + (size * 0.24), x + (size * 0.50), y + (size * 0.76))
    else:
        _draw_tag_line(pdf, x + (size * 0.24), y + (size * 0.76), x + (size * 0.76), y + (size * 0.24))


def _draw_tag_glyph(pdf, x: float, baseline_y: float, shape: int | None, color: tuple[float, float, float], icon_size: float) -> float:
    glyph_y = baseline_y - (icon_size * 0.08)
    _set_stroke_color(pdf, color)
    _set_fill_color(pdf, color)
    if shape in _CHECKBOX_SHAPES:
        _draw_tag_rect(pdf, x, glyph_y - (icon_size * 0.10), icon_size, icon_size)
        inner_x = x + (icon_size * 0.08)
        inner_y = glyph_y
        inner_size = icon_size * 0.84
        if shape in {4, 5, 6}:
            _draw_star_icon(pdf, inner_x, inner_y, inner_size)
        elif shape in {7, 8, 9}:
            _draw_question_icon(pdf, inner_x, inner_y, inner_size)
        elif shape in {10, 11, 12}:
            _draw_arrow_icon(pdf, inner_x, inner_y, inner_size, "right")
        elif shape in {89, 90, 91, 92, 93, 97, 98, 99}:
            _draw_flag_icon(pdf, inner_x, inner_y, inner_size)
        elif shape in {94, 95, 96}:
            _draw_contact_icon(pdf, inner_x, inner_y, inner_size)
        else:
            _draw_checkmark_icon(pdf, inner_x, inner_y, inner_size)
        return icon_size
    if shape in _STAR_SHAPES:
        _draw_star_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _QUESTION_SHAPES:
        _draw_question_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _EXCLAMATION_SHAPES:
        _draw_tag_line(pdf, x + (icon_size * 0.50), glyph_y + (icon_size * 0.22), x + (icon_size * 0.50), glyph_y + (icon_size * 0.78))
        _draw_tag_rect(pdf, x + (icon_size * 0.45), glyph_y + (icon_size * 0.06), icon_size * 0.10, icon_size * 0.10, fill=True)
        return icon_size
    if shape in _ARROW_RIGHT_SHAPES:
        _draw_arrow_icon(pdf, x, glyph_y, icon_size, "right")
        return icon_size
    if shape in _ARROW_LEFT_SHAPES:
        _draw_arrow_icon(pdf, x, glyph_y, icon_size, "left")
        return icon_size
    if shape in _ARROW_UP_SHAPES:
        _draw_arrow_icon(pdf, x, glyph_y, icon_size, "up")
        return icon_size
    if shape in _ARROW_DOWN_SHAPES:
        _draw_arrow_icon(pdf, x, glyph_y, icon_size, "down")
        return icon_size
    if shape in _FLAG_SHAPES:
        _draw_flag_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _CHECKMARK_SHAPES:
        _draw_checkmark_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _CONTACT_SHAPES:
        _draw_contact_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _MUSIC_SHAPES:
        _draw_music_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _CALENDAR_SHAPES:
        _draw_calendar_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    if shape in _TIME_SHAPES:
        _draw_clock_icon(pdf, x, glyph_y, icon_size)
        return icon_size
    _draw_generic_badge(pdf, x, glyph_y, icon_size, shape)
    return icon_size


def _render_note_tag(pdf, tag, x: float, baseline_y: float, options: PdfSaveOptions | None) -> float:
    icon_size = _normalize_tag_icon_size(options)
    icon_path = _find_tag_icon_path(tag, options)
    if icon_path is not None:
        try:
            from reportlab.lib.utils import ImageReader

            image = ImageReader(str(icon_path))
            pdf.drawImage(image, x, baseline_y - (icon_size * 0.18), width=icon_size, height=icon_size, preserveAspectRatio=True, mask="auto")
            return icon_size
        except Exception:
            pass

    shape = _tag_value(tag, "Icon", "shape")
    return _draw_tag_glyph(pdf, x, baseline_y, shape, _tag_color(shape), icon_size)


def _dedupe_tags(tags) -> list[object]:
    seen: set[tuple[object, ...]] = set()
    result: list[object] = []
    for tag in tags or []:
        key = (
            _tag_value(tag, "Icon", "shape"),
            _tag_value(tag, "Label", "label"),
            _tag_value(tag, "FontColor", "text_color"),
            _tag_value(tag, "Highlight", "highlight_color"),
            _tag_value(tag, "CreationTime", "created"),
            _tag_value(tag, "CompletedTime", "completed"),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
    return result


def _tag_block_width(pdf, tags, options: PdfSaveOptions | None) -> float:
    deduped = _dedupe_tags(tags)
    if not deduped:
        return 0.0
    gap = _normalize_tag_icon_gap(options)
    icon_size = _normalize_tag_icon_size(options)
    return (len(deduped) * icon_size) + (len(deduped) * gap)


def _render_note_tags(pdf, tags, x: float, baseline_y: float, options: PdfSaveOptions | None) -> float:
    deduped = _dedupe_tags(tags)
    if not deduped:
        return 0.0
    gap = _normalize_tag_icon_gap(options)
    consumed = 0.0
    for tag in reversed(deduped):
        consumed += _render_note_tag(pdf, tag, x + consumed, baseline_y, options)
        consumed += gap
    return consumed


def _tags_for_node(node):
    return _dedupe_tags(getattr(node, "Tags", None) or [])


def _simple_text_style(font_size: float, *, bold: bool = False, italic: bool = False, font_color: int | None = None):
    return SimpleNamespace(
        FontName=None,
        FontSize=font_size,
        FontColor=font_color,
        Highlight=None,
        IsBold=bold,
        IsItalic=italic,
        IsUnderline=False,
        IsStrikethrough=False,
        IsSuperscript=False,
        IsSubscript=False,
        HyperlinkAddress=None,
        IsHyperlink=False,
    )


def _simple_text_run(text: str, font_size: float, *, bold: bool = False, italic: bool = False, font_color: int | None = None):
    return SimpleNamespace(Text=text, Style=_simple_text_style(font_size, bold=bold, italic=italic, font_color=font_color))


def _attachment_display_name(attached_file) -> str:
    name = (getattr(attached_file, "FileName", None) or "").strip()
    return name or "attachment.bin"


def _number_list_payload(fmt: str | None) -> str:
    if not fmt:
        return ""
    if len(fmt) > 1 and ord(fmt[0]) == len(fmt) - 1:
        return fmt[1:]
    return fmt


def _to_roman(value: int) -> str:
    if value <= 0:
        return str(value)
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    result: list[str] = []
    for amount, numeral in numerals:
        while remaining >= amount:
            result.append(numeral)
            remaining -= amount
    return "".join(result)


def _to_alpha(value: int) -> str:
    if value <= 0:
        return str(value)
    current = value
    chars: list[str] = []
    while current > 0:
        current -= 1
        chars.append(chr(ord("a") + (current % 26)))
        current //= 26
    return "".join(reversed(chars))


def _format_list_number(value: int, number_format: int) -> str:
    if number_format == 4:
        return _to_alpha(value)
    if number_format == 3:
        return _to_alpha(value).upper()
    if number_format == 2:
        return _to_roman(value).lower()
    if number_format == 1:
        return _to_roman(value)
    return str(value)


def _resolve_list_marker_text(number_list, depth: int, list_state: dict[tuple[int, str], int]) -> str:
    fmt = getattr(number_list, "Format", None)
    payload = _number_list_payload(fmt)
    if not payload:
        return ""

    marker_index = payload.find("\ufffd")
    if marker_index == -1:
        return payload

    number_format_char = payload[marker_index + 1] if marker_index + 1 < len(payload) else "\x00"
    key = (depth, payload)
    restart = getattr(number_list, "Restart", None)
    if isinstance(restart, int) and restart > 0:
        current_value = restart
    else:
        current_value = list_state.get(key, 0) + 1
    list_state[key] = current_value

    prefix = payload[:marker_index]
    suffix = payload[marker_index + 2 :]
    return f"{prefix}{_format_list_number(current_value, ord(number_format_char))}{suffix}"


def _render_outline_list_item(pdf, outline_element, rich_text, cursor_y: float, page_width: float, page_height: float, start_x: float, max_width: float | None, depth: int, options: PdfSaveOptions | None, list_state: dict[tuple[int, str], int]) -> tuple[float, float]:
    item_start_x = start_x + (depth * _OUTLINE_LEVEL_INDENT)
    tag_offset = _tag_block_width(pdf, _tags_for_node(rich_text), options)
    if tag_offset:
        _render_note_tags(pdf, _tags_for_node(rich_text), item_start_x, cursor_y, options)

    marker_text = ""
    number_list = getattr(outline_element, "NumberList", None)
    if number_list is not None:
        marker_text = _resolve_list_marker_text(number_list, depth, list_state)

    marker_width = 0.0
    marker_x = item_start_x + tag_offset
    if marker_text:
        marker_font = _register_font_variant("sans", False, False)
        marker_width = max(_string_width(pdf, marker_text, marker_font, 11.0), _OUTLINE_MARKER_MIN_WIDTH)
        pdf.setFont(marker_font, 11.0)
        _set_fill_color(pdf, (0.0, 0.0, 0.0))
        pdf.drawString(marker_x, cursor_y, marker_text)

    text_start_x = marker_x + (marker_width + _OUTLINE_MARKER_GAP if marker_width else 0.0)
    render_max_width = max(max_width - (text_start_x - start_x), 1.0) if max_width is not None else None
    _, cursor_y = _render_runs(pdf, _iter_runs(rich_text), text_start_x, cursor_y, page_width, page_height, default_font="Arial", default_size=11.0)
    return cursor_y, text_start_x


def _render_outline_element(pdf, outline_element, cursor_y: float, page_width: float, page_height: float, start_x: float, max_width: float | None, depth: int, options: PdfSaveOptions | None, list_state: dict[tuple[int, str], int]) -> float:
    from ..model import OutlineElement, RichText

    text_start_x = start_x + ((depth + 1) * _OUTLINE_LEVEL_INDENT)
    rendered_rich_text = False

    for child in outline_element:
        if isinstance(child, RichText):
            if not _plain_text_from_rich_text(child):
                continue
            cursor_y, text_start_x = _render_outline_list_item(
                pdf,
                outline_element,
                child,
                cursor_y,
                page_width,
                page_height,
                start_x,
                max_width,
                depth,
                options,
                list_state,
            )
            rendered_rich_text = True
            continue

        child_start_x = text_start_x if rendered_rich_text else (start_x + (depth * _OUTLINE_LEVEL_INDENT))
        child_max_width = max(max_width - (child_start_x - start_x), 1.0) if max_width is not None else None
        next_depth = depth + 1 if isinstance(child, OutlineElement) else depth
        cursor_y = _render_outline_content(
            pdf,
            child,
            cursor_y,
            page_width,
            page_height,
            child_start_x if next_depth == depth else start_x,
            max_width=child_max_width if next_depth == depth else max_width,
            options=options,
            list_state=list_state,
            outline_depth=next_depth,
        )

    return cursor_y


def _plain_text_from_rich_text(rich_text) -> str:
    return _sanitize_text(getattr(rich_text, "Text", "")).strip()


def _has_ancestor_of_type(node, node_type: type) -> bool:
    current = getattr(node, "ParentNode", None)
    while current is not None:
        if isinstance(current, node_type):
            return True
        current = getattr(current, "ParentNode", None)
    return False


def _outline_x_position(outline) -> float:
    return _DEFAULT_PAGE_MARGIN_POINTS + max(float(getattr(outline, "X", 0.0) or 0.0), 0.0) * _POINTS_PER_HALF_INCH


def _outline_y_position(content_origin_y: float, outline) -> float:
    return content_origin_y - max(float(getattr(outline, "Y", 0.0) or 0.0), 0.0) * _POINTS_PER_HALF_INCH


def _container_width(page_width: float, start_x: float, max_width: float | None = None) -> float:
    available_width = max(page_width - _RIGHT_MARGIN - start_x, 1.0)
    if max_width is None or max_width <= 0:
        return available_width
    return max(min(max_width, available_width), 1.0)


def _aligned_x(start_x: float, content_width: float, container_width: float, horizontal_alignment: HorizontalAlignment | None) -> float:
    if horizontal_alignment == HorizontalAlignment.Center:
        return start_x + max((container_width - content_width) / 2.0, 0.0)
    if horizontal_alignment == HorizontalAlignment.Right:
        return start_x + max(container_width - content_width, 0.0)
    return start_x


def _scale_dimensions_to_fit(width: float, height: float, max_width: float, max_height: float) -> tuple[float, float]:
    if width <= 0 or height <= 0:
        return width, height
    width_scale = max_width / width if max_width > 0 else 1.0
    height_scale = max_height / height if max_height > 0 else 1.0
    scale = min(width_scale, height_scale, 1.0)
    return width * scale, height * scale


def _resolve_image_draw_size(image, image_reader, page_width: float, cursor_y: float, start_x: float = _LEFT_MARGIN, max_width: float | None = None) -> tuple[float, float]:
    pixel_width, pixel_height = image_reader.getSize()
    aspect_ratio = (float(pixel_width) / float(pixel_height)) if pixel_width and pixel_height else 1.0

    width_cm = max(float(getattr(image, "Width", 0.0) or 0.0), 0.0)
    height_cm = max(float(getattr(image, "Height", 0.0) or 0.0), 0.0)
    if width_cm > 0 and height_cm > 0:
        draw_width = width_cm * _POINTS_PER_IMAGE_CM
        draw_height = height_cm * _POINTS_PER_IMAGE_CM
    elif width_cm > 0:
        draw_width = width_cm * _POINTS_PER_IMAGE_CM
        draw_height = draw_width / aspect_ratio if aspect_ratio > 0 else draw_width
    elif height_cm > 0:
        draw_height = height_cm * _POINTS_PER_IMAGE_CM
        draw_width = draw_height * aspect_ratio
    else:
        draw_width = float(pixel_width) * 0.75 if pixel_width else 220.0
        draw_height = float(pixel_height) * 0.75 if pixel_height else 160.0

    available_width = _container_width(page_width, start_x, max_width)
    max_height = max(cursor_y - _BOTTOM_MARGIN, 1.0)
    return _scale_dimensions_to_fit(draw_width, draw_height, available_width, max_height)


def _rich_text_alignment(rich_text) -> HorizontalAlignment | None:
    return getattr(rich_text, "Alignment", None)


def _measure_runs_width(pdf, runs, default_font: str, default_size: float, default_bold: bool = False) -> float:
    total = 0.0
    for run in runs:
        style = run.Style
        text = _sanitize_text(getattr(run, "Text", ""))
        if not text:
            continue
        font_size = max(float(getattr(style, "FontSize", None) or default_size), 1.0)
        font_name = _font_name_for_style(style, default_font, text=text, default_bold=default_bold)
        total += _string_width(pdf, text, font_name, font_size)
    return total


def _render_aligned_single_line_rich_text(pdf, runs, cursor_y: float, start_x: float, container_width: float, horizontal_alignment: HorizontalAlignment, default_font: str, default_size: float, default_bold: bool = False) -> float:
    line_width = _measure_runs_width(pdf, runs, default_font, default_size, default_bold=default_bold)
    x = _aligned_x(start_x, line_width, container_width, horizontal_alignment)
    for run in runs:
        text = _sanitize_text(getattr(run, "Text", ""))
        if not text:
            continue
        x = _draw_segment(pdf, x, cursor_y, text, run.Style, default_font, default_size, default_bold=default_bold)
    return cursor_y - (default_size * 1.35)


def _table_cell_text(cell) -> str:
    from ..model import RichText

    texts = [_plain_text_from_rich_text(rich_text) for rich_text in cell.GetChildNodes(RichText)]
    return "\n".join(text for text in texts if text)


def _inline_tag_text(tag) -> str:
    shape = getattr(tag, "shape", None)
    if shape in _CHECKBOX_SHAPES:
        return "☐"
    symbol, textual = _tag_symbol(tag)
    return symbol if not textual else symbol.strip()


def _inline_tag_prefix(tags) -> str:
    parts = [_inline_tag_text(tag) for tag in reversed(_dedupe_tags(tags))]
    parts = [part for part in parts if part]
    return "".join(parts)


def _paragraph_font_name_for_text(text: str, *, bold: bool = False, italic: bool = False) -> str:
    return _register_font_variant("sans", bold, italic, require_unicode=_text_requires_unicode_font(text))


def _paragraph_for_table_text(text: str, max_width: float, *, left_indent: float = 0.0, default_alignment: HorizontalAlignment | None = None, font_size: float = 11.0, leading: float = 13.0):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    escaped_text = escape(text).replace("\n", "<br/>")
    style = ParagraphStyle(
        name="AsposeNoteStructuredTableCell",
        fontName=_paragraph_font_name_for_text(text),
        fontSize=font_size,
        leading=leading,
        alignment=_paragraph_alignment_value(default_alignment),
        leftIndent=max(left_indent, 0.0),
        wordWrap="CJK",
    )
    paragraph = Paragraph(escaped_text, style)
    paragraph.width = max_width
    return paragraph


def _table_outline_prefix_width(tags, marker_text: str, font_size: float) -> float:
    width = _tag_block_width(None, tags, None)
    if marker_text:
        try:
            from reportlab.pdfbase import pdfmetrics

            marker_font = _register_font_variant("sans", False, False, require_unicode=_text_requires_unicode_font(marker_text))
            marker_width = pdfmetrics.stringWidth(marker_text, marker_font, font_size)
        except Exception:
            marker_width = len(marker_text) * font_size * 0.55
        width += max(marker_width, _OUTLINE_MARKER_MIN_WIDTH - 2.0) + 3.0
    return width


def _centered_tag_baseline(top_y: float, block_height: float, icon_size: float) -> float:
    center_y = top_y - (block_height / 2.0)
    return center_y - (icon_size * 0.42)


def _table_outline_item_flowable(text: str, tags, marker_text: str, max_width: float, indent: float, default_alignment: HorizontalAlignment | None = None, font_size: float = 9.0, leading: float = 11.0):
    from reportlab.platypus import Flowable, Table as FlowTable, TableStyle

    class OutlinePrefixFlowable(Flowable):
        def __init__(self) -> None:
            super().__init__()
            self.width = indent + _table_outline_prefix_width(tags, marker_text, font_size)
            self.height = max(leading, _normalize_tag_icon_size(None) + 2.0)

        def wrap(self, aW, aH):
            return min(self.width, aW), self.height

        def draw(self):
            x = indent
            baseline_y = max(font_size * 0.15, _normalize_tag_icon_size(None) * 0.18)
            if tags:
                _render_note_tags(self.canv, tags, x, baseline_y, None)
                x += _tag_block_width(self.canv, tags, None)
            if marker_text:
                marker_font = _register_font_variant("sans", False, False, require_unicode=_text_requires_unicode_font(marker_text))
                self.canv.setFont(marker_font, font_size)
                _set_fill_color(self.canv, (0.0, 0.0, 0.0))
                self.canv.drawString(x, baseline_y, marker_text)

    prefix = OutlinePrefixFlowable()
    prefix_width = min(prefix.width, max(max_width * 0.45, prefix.width))
    text_width = max(max_width - prefix.width, 1.0)
    paragraph = _paragraph_for_table_text(
        text,
        text_width,
        default_alignment=default_alignment,
        font_size=font_size,
        leading=leading,
    )
    flowable = FlowTable([[prefix, paragraph]], colWidths=[prefix_width, text_width])
    flowable.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return flowable


def _iter_renderable_descendants(node):
    from ..model import AttachedFile, Image, RichText

    for child in node:
        if isinstance(child, (AttachedFile, Image, RichText)):
            yield child
            continue
        yield from _iter_renderable_descendants(child)


def _table_contains_images(table) -> bool:
    from ..model import Image

    return bool(table.GetChildNodes(Image))


def _paragraph_alignment_value(alignment: HorizontalAlignment | None) -> Literal[0, 1, 2]:
    if alignment == HorizontalAlignment.Center:
        return 1
    if alignment == HorizontalAlignment.Right:
        return 2
    return 0


def _flowable_alignment_value(alignment: HorizontalAlignment | None) -> Literal["LEFT", "CENTER", "RIGHT"]:
    if alignment == HorizontalAlignment.Center:
        return "CENTER"
    if alignment == HorizontalAlignment.Right:
        return "RIGHT"
    return "LEFT"


def _rich_text_to_paragraph(rich_text, max_width: float, default_alignment: HorizontalAlignment | None = None):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    text = escape(_plain_text_from_rich_text(rich_text)).replace("\n", "<br/>")
    if not text:
        return None
    alignment = _rich_text_alignment(rich_text) or default_alignment
    style = ParagraphStyle(
        name="AsposeNoteTableCell",
        fontName=_register_font_variant("sans", False, False),
        fontSize=11,
        leading=13,
        alignment=_paragraph_alignment_value(alignment),
        wordWrap="CJK",
    )
    paragraph = Paragraph(text, style)
    paragraph.width = max_width
    return paragraph


def _attached_file_name_to_paragraph(attached_file, max_width: float, default_alignment: HorizontalAlignment | None = None):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    text = escape(_attachment_display_name(attached_file))
    style = ParagraphStyle(
        name="AsposeNoteAttachmentName",
        fontName=_register_font_variant("sans", False, False),
        fontSize=10,
        leading=12,
        alignment=_paragraph_alignment_value(default_alignment),
        wordWrap="CJK",
    )
    paragraph = Paragraph(text, style)
    paragraph.width = max_width
    return paragraph


def _attached_file_to_flowable(attached_file, max_width: float, default_alignment: HorizontalAlignment | None = None):
    from reportlab.platypus import Flowable

    tags = _tags_for_node(attached_file)
    if not tags:
        return None

    class AttachmentTagFlowable(Flowable):
        def __init__(self) -> None:
            super().__init__()
            self.hAlign = _flowable_alignment_value(default_alignment)
            self.width = min(_tag_block_width(None, tags, None), max_width)
            self.height = _normalize_tag_icon_size(None)

        def wrap(self, aW, aH):
            width = min(self.width, aW)
            height = min(self.height, aH if aH > 0 else self.height)
            return width, height

        def draw(self):
            baseline_y = _normalize_tag_icon_size(None) * 0.18
            _render_note_tags(self.canv, tags, 0.0, baseline_y, None)

    return AttachmentTagFlowable()


def _image_to_flowable(image, max_width: float):
    from reportlab.platypus import Image as FlowImage
    from reportlab.lib.utils import ImageReader

    if not image.Bytes:
        return None
    image_reader = ImageReader(BytesIO(bytes(image.Bytes)))
    draw_width, draw_height = _resolve_image_draw_size(image, image_reader, max_width, 10_000.0, start_x=0.0, max_width=max_width)
    flowable = FlowImage(BytesIO(bytes(image.Bytes)), width=draw_width, height=draw_height)
    flowable.hAlign = _flowable_alignment_value(getattr(image, "Alignment", None))
    return flowable


def _table_cell_alignment(cell) -> HorizontalAlignment | None:
    from ..model import Image, RichText

    for node in _iter_renderable_descendants(cell):
        if isinstance(node, Image) and getattr(node, "Alignment", None) is not None:
            return node.Alignment
        if isinstance(node, RichText):
            alignment = _rich_text_alignment(node)
            if alignment is not None:
                return alignment
    return None


def _table_outline_flowables(node, max_width: float, default_alignment: HorizontalAlignment | None = None, *, depth: int = 0, list_state: dict[tuple[int, str], int] | None = None):
    from reportlab.platypus import Spacer
    from ..model import AttachedFile, Image, OutlineElement, RichText

    if list_state is None:
        list_state = {}

    flowables = []
    for child in node:
        if isinstance(child, OutlineElement):
            child_flowables = _table_outline_flowables(
                child,
                max_width,
                default_alignment,
                depth=depth + 1,
                list_state=list_state,
            )
            for child_flowable in child_flowables:
                if flowables and not isinstance(child_flowable, Spacer):
                    flowables.append(Spacer(1, 2))
                flowables.append(child_flowable)
            continue

        if isinstance(child, RichText):
            text = _plain_text_from_rich_text(child)
            if not text:
                continue
            tags = _tags_for_node(child)
            marker_text = ""
            parent_outline = getattr(child, "ParentNode", None)
            if isinstance(parent_outline, OutlineElement) and getattr(parent_outline, "NumberList", None) is not None:
                marker_text = _resolve_list_marker_text(parent_outline.NumberList, max(depth - 1, 0), list_state)
            paragraph = _table_outline_item_flowable(
                text,
                tags,
                marker_text,
                max(max_width, 1.0),
                max(depth - 1, 0) * (_OUTLINE_LEVEL_INDENT * 0.8),
                default_alignment=default_alignment or _rich_text_alignment(child),
                font_size=9.0,
                leading=11.0,
            )
            if flowables:
                flowables.append(Spacer(1, 2))
            flowables.append(paragraph)
            continue

        if isinstance(child, Image):
            flowable = _image_to_flowable(child, max(max_width, 1.0))
            if flowable is not None:
                if flowables:
                    flowables.append(Spacer(1, 4))
                flowables.append(flowable)
            continue

        if isinstance(child, AttachedFile):
            attachment_flowables = [
                _attached_file_name_to_paragraph(child, max(max_width, 1.0), default_alignment=default_alignment),
                _attached_file_to_flowable(child, max(max_width, 1.0), default_alignment=default_alignment),
            ]
            for attachment_flowable in attachment_flowables:
                if attachment_flowable is None:
                    continue
                if flowables:
                    flowables.append(Spacer(1, 4))
                flowables.append(attachment_flowable)
            continue

        nested_flowables = _table_outline_flowables(
            child,
            max_width,
            default_alignment,
            depth=depth,
            list_state=list_state,
        )
        for nested_flowable in nested_flowables:
            if flowables and not isinstance(nested_flowable, Spacer):
                flowables.append(Spacer(1, 2))
            flowables.append(nested_flowable)

    return flowables


def _table_cell_flowables(cell, max_width: float, default_alignment: HorizontalAlignment | None = None):
    from reportlab.platypus import Spacer

    flowables = _table_outline_flowables(cell, max_width, default_alignment, depth=0, list_state={})
    if flowables:
        return flowables

    fallback_flowables = []
    for node in _iter_renderable_descendants(cell):
        if getattr(node, "Text", None):
            paragraph = _paragraph_for_table_text(
                _plain_text_from_rich_text(node),
                max(max_width, 1.0),
                default_alignment=default_alignment,
            )
            fallback_flowables.append(paragraph)
    return fallback_flowables or [Spacer(1, 1)]


def _resolve_table_column_widths(table, column_count: int, available_width: float) -> list[float]:
    if column_count <= 0:
        return []

    raw_widths = [
        float(width)
        for width in [getattr(column, "Width", None) for column in getattr(table, "Columns", getattr(table, "ColumnWidths", []))]
        if width is not None and float(width) > 1.0
    ]
    if len(raw_widths) >= column_count:
        total_width = sum(raw_widths[:column_count])
        if total_width > 0:
            scale = available_width / total_width
            return [max(width * scale, 36.0) for width in raw_widths[:column_count]]

    equal_width = max(available_width / column_count, 36.0)
    return [equal_width] * column_count


def _render_table(pdf, table, cursor_y: float, page_width: float, page_height: float, start_x: float, max_width: float | None = None, options: PdfSaveOptions | None = None) -> float:
    try:
        from reportlab.lib import colors
        from reportlab.platypus import Table as FlowTable
        from reportlab.platypus import TableStyle
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab") from exc

    rows: list[list[object]] = []
    column_count = 0
    contains_images = _table_contains_images(table)
    rendered_rows = [list(row) for row in table]
    for row in rendered_rows:
        column_count = max(column_count, len(row))

    if not rendered_rows or column_count == 0:
        return cursor_y

    table_tags = _tags_for_node(table)
    tag_offset = _tag_block_width(pdf, table_tags, options)
    tag_x = start_x
    if tag_offset:
        start_x += tag_offset
        if max_width is not None:
            max_width = max(max_width - tag_offset, 1.0)

    available_width = max(_container_width(page_width, start_x, max_width), 72.0)
    column_widths = _resolve_table_column_widths(table, column_count, available_width)
    alignment_commands: list[tuple[str, tuple[int, int], tuple[int, int], str]] = []
    normalized_rows = []
    for row_index, row in enumerate(rendered_rows):
        rendered_row = []
        for index, cell in enumerate(row):
            cell_width = column_widths[index] if index < len(column_widths) else (available_width / max(column_count, 1))
            cell_alignment = _table_cell_alignment(cell)
            rendered_row.append(_table_cell_flowables(cell, max(cell_width - 12.0, 1.0), default_alignment=cell_alignment))
            alignment_commands.append(("ALIGN", (index, row_index), (index, row_index), _flowable_alignment_value(cell_alignment)))
        rendered_row.extend([""] * (column_count - len(rendered_row)))
        normalized_rows.append(rendered_row)

    grid_color = colors.Color(0.55, 0.55, 0.55)

    flowable = FlowTable(normalized_rows, colWidths=column_widths)
    flowable.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), _register_font_variant("sans", False, False)),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("LEADING", (0, 0), (-1, -1), 13),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, grid_color),
                *alignment_commands,
            ]
        )
    )

    pending_parts = [flowable]
    drew_table_tags = False
    while pending_parts:
        current_part = pending_parts.pop(0)
        available_height = max(cursor_y - _BOTTOM_MARGIN, 1.0)
        _, height_used = current_part.wrapOn(pdf, available_width, available_height)
        if height_used <= available_height:
            current_part.drawOn(pdf, start_x, cursor_y - height_used)
            if tag_offset and not drew_table_tags:
                _render_note_tags(
                    pdf,
                    table_tags,
                    tag_x,
                    _centered_tag_baseline(cursor_y, height_used, _normalize_tag_icon_size(options)),
                    options,
                )
                drew_table_tags = True
            cursor_y -= height_used
            if pending_parts:
                cursor_y = _show_page(pdf, page_height)
            continue

        parts = current_part.splitOn(pdf, available_width, available_height)
        if parts:
            pending_parts = list(parts) + pending_parts
            continue

        cursor_y = _show_page(pdf, page_height)

    return cursor_y - 12


def _render_image(pdf, image, cursor_y: float, page_width: float, page_height: float, start_x: float, max_width: float | None = None, options: PdfSaveOptions | None = None) -> float:
    try:
        from reportlab.lib.utils import ImageReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab") from exc

    if not image.Bytes:
        return cursor_y
    if cursor_y < 180:
        cursor_y = _show_page(pdf, page_height)

    image_tags = _tags_for_node(image)
    tag_offset = _tag_block_width(pdf, image_tags, options)
    tag_x = start_x
    if tag_offset:
        start_x += tag_offset
        if max_width is not None:
            max_width = max(max_width - tag_offset, 1.0)

    try:
        img = ImageReader(BytesIO(bytes(image.Bytes)))
        draw_width, draw_height = _resolve_image_draw_size(image, img, page_width, cursor_y, start_x=start_x, max_width=max_width)
        container_width = _container_width(page_width, start_x, max_width)
        draw_x = _aligned_x(start_x, draw_width, container_width, getattr(image, "Alignment", None))
        draw_y = max(_BOTTOM_MARGIN, cursor_y - draw_height)
        pdf.drawImage(img, draw_x, draw_y, width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")
        if tag_offset:
            _render_note_tags(
                pdf,
                image_tags,
                tag_x,
                _centered_tag_baseline(cursor_y, draw_height, _normalize_tag_icon_size(options)),
                options,
            )
        if getattr(image, "HyperlinkUrl", None) and hasattr(pdf, "linkURL"):
            pdf.linkURL(str(image.HyperlinkUrl), (draw_x, draw_y, draw_x + draw_width, draw_y + draw_height), relative=0)
        return cursor_y - draw_height - 12
    except Exception:
        pdf.setFont(_register_font_variant("sans", False, True), 10)
        pdf.drawString(start_x, cursor_y, image.FileName or "[image]")
        return cursor_y - 14


def _render_attached_file(pdf, attached_file, cursor_y: float, page_width: float, page_height: float, start_x: float, max_width: float | None = None, options: PdfSaveOptions | None = None) -> float:
    if cursor_y < 96:
        cursor_y = _show_page(pdf, page_height)

    tags = _tags_for_node(attached_file)
    tag_offset = _tag_block_width(pdf, tags, options)
    if tag_offset:
        _render_note_tags(pdf, tags, start_x, cursor_y, options)

    render_start_x = start_x + tag_offset
    render_max_width = max(max_width - tag_offset, 1.0) if max_width is not None and tag_offset else max_width
    _, cursor_y = _render_runs(
        pdf,
        [_simple_text_run(_attachment_display_name(attached_file), 11.0)],
        render_start_x,
        cursor_y,
        page_width,
        page_height,
        default_font="Arial",
        default_size=11.0,
    )
    if tag_offset:
        return min(cursor_y, cursor_y - 0.0)
    return cursor_y


def _render_outline_content(pdf, node, cursor_y: float, page_width: float, page_height: float, start_x: float, max_width: float | None = None, options: PdfSaveOptions | None = None, list_state: dict[tuple[int, str], int] | None = None, outline_depth: int = 0) -> float:
    from ..model import AttachedFile, OutlineElement, RichText, Table
    from ..model import Image as NoteImage

    if list_state is None:
        list_state = {}

    if isinstance(node, OutlineElement):
        return _render_outline_element(pdf, node, cursor_y, page_width, page_height, start_x, max_width, outline_depth, options, list_state)

    if isinstance(node, RichText):
        if _has_ancestor_of_type(node, Table):
            return cursor_y
        if not _plain_text_from_rich_text(node):
            return cursor_y
        runs = _iter_runs(node)
        alignment = _rich_text_alignment(node)
        tag_offset = _tag_block_width(pdf, _tags_for_node(node), options)
        text = "".join(_sanitize_text(getattr(run, "Text", "")) for run in runs)
        render_start_x = start_x + tag_offset
        render_max_width = max(max_width - tag_offset, 1.0) if max_width is not None and tag_offset else max_width
        if tag_offset:
            _render_note_tags(pdf, _tags_for_node(node), start_x, cursor_y, options)
        container_width = _container_width(page_width, render_start_x, render_max_width)
        if not tag_offset and alignment in {HorizontalAlignment.Center, HorizontalAlignment.Right} and "\n" not in text:
            return _render_aligned_single_line_rich_text(
                pdf,
                runs,
                cursor_y,
                render_start_x,
                container_width,
                alignment,
                default_font="Arial",
                default_size=11.0,
            )
        _, cursor_y = _render_runs(pdf, runs, render_start_x, cursor_y, page_width, page_height, default_font="Arial", default_size=11.0)
        return cursor_y

    if isinstance(node, Table):
        return _render_table(pdf, node, cursor_y, page_width, page_height, start_x=start_x, max_width=max_width, options=options)

    if isinstance(node, NoteImage):
        return _render_image(pdf, node, cursor_y, page_width, page_height, start_x=start_x, max_width=max_width, options=options)

    if isinstance(node, AttachedFile):
        return _render_attached_file(pdf, node, cursor_y, page_width, page_height, start_x=start_x, max_width=max_width, options=options)

    for child in node:
        cursor_y = _render_outline_content(pdf, child, cursor_y, page_width, page_height, start_x, max_width=max_width, options=options, list_state=list_state, outline_depth=outline_depth)
    return cursor_y


def write_pdf(document, options: PdfSaveOptions) -> bytes:
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab") from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    width, height = getattr(pdf, "_pagesize", (612.0, 792.0))

    pages = list(document)
    start = max(options.PageIndex, 0)
    selected = pages[start : start + options.PageCount if options.PageCount is not None else None]
    if not selected:
        selected = [None]

    for index, page in enumerate(selected):
        cursor_y = height - _TOP_MARGIN
        if page is not None:
            from ..model import AttachedFile, Image, Outline, Page, RichText, Table, TableCell

            current_page = cast(Page, page)

            title_nodes: set[int] = set()
            if current_page.Title is not None:
                if current_page.Title.TitleText is not None:
                    title_nodes.add(id(current_page.Title.TitleText))
                    cursor_y = _render_rich_text(pdf, current_page.Title.TitleText, cursor_y, width, height, start_x=_LEFT_MARGIN, default_font="Arial", default_size=14.0, options=options)

                meta_nodes = []
                if current_page.Title.TitleDate is not None:
                    title_nodes.add(id(current_page.Title.TitleDate))
                    meta_nodes.append(current_page.Title.TitleDate)
                if current_page.Title.TitleTime is not None:
                    title_nodes.add(id(current_page.Title.TitleTime))
                    meta_nodes.append(current_page.Title.TitleTime)
                if meta_nodes:
                    cursor_y = _render_inline_rich_texts(pdf, meta_nodes, cursor_y, width, height, start_x=_LEFT_MARGIN, default_font="Arial", default_size=9.0)
                cursor_y -= 14

            content_origin_y = cursor_y
            rendered_outline_text_ids: set[int] = set()
            next_outline_y = content_origin_y
            for outline in current_page.GetChildNodes(Outline):
                outline_cursor_y = min(_outline_y_position(content_origin_y, outline), next_outline_y)
                outline_start_x = _outline_x_position(outline)
                outline_max_width = max(float(getattr(outline, "Width", 0.0) or 0.0), 0.0) * _POINTS_PER_HALF_INCH or None
                for rich_text in outline.GetChildNodes(RichText):
                    rendered_outline_text_ids.add(id(rich_text))
                outline_cursor_y = _render_outline_content(pdf, outline, outline_cursor_y, width, height, outline_start_x, max_width=outline_max_width, options=options)
                next_outline_y = outline_cursor_y - 8

            cursor_y = min(cursor_y, next_outline_y)

            for rich_text in current_page.GetChildNodes(RichText):
                if id(rich_text) in title_nodes or id(rich_text) in rendered_outline_text_ids or _has_ancestor_of_type(rich_text, TableCell) or _has_ancestor_of_type(rich_text, Outline):
                    continue
                if not _plain_text_from_rich_text(rich_text):
                    continue
                cursor_y = _render_rich_text(pdf, rich_text, cursor_y, width, height, start_x=_LEFT_MARGIN, default_font="Arial", default_size=11.0, options=options)

            for table in current_page.GetChildNodes(Table):
                if _has_ancestor_of_type(table, Outline):
                    continue
                cursor_y = _render_table(pdf, table, cursor_y, width, height, start_x=_LEFT_MARGIN, options=options)

            for image in current_page.GetChildNodes(Image):
                if _has_ancestor_of_type(image, Outline):
                    continue
                if not image.Bytes:
                    continue
                cursor_y = _render_image(pdf, image, cursor_y, width, height, start_x=_LEFT_MARGIN, options=options)

            for attached_file in current_page.GetChildNodes(AttachedFile):
                if _has_ancestor_of_type(attached_file, Outline) or _has_ancestor_of_type(attached_file, TableCell):
                    continue
                cursor_y = _render_attached_file(pdf, attached_file, cursor_y, width, height, start_x=_LEFT_MARGIN, options=options)

            if index != len(selected) - 1:
                pdf.showPage()
        else:
            pdf.setFont(_register_font_variant("sans", False, False), 12)
            pdf.drawString(_LEFT_MARGIN, cursor_y, document.DisplayName or "Empty document")

    pdf.save()
    return buffer.getvalue()