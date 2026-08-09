"""Name and introduce additional examples for repository visitors."""

from __future__ import annotations

import re

from readme_agent.readme.document_structure import heading_identity

_GENERIC_TITLES = {
    "additional example",
    "additional workflow",
    "example",
    "quick start",
}
_ACTION_GERUNDS = {
    "access": "accessing",
    "assign": "assigning",
    "build": "building",
    "convert": "converting",
    "count": "counting",
    "create": "creating",
    "export": "exporting",
    "explore": "exploring",
    "extract": "extracting",
    "generate": "generating",
    "host": "hosting",
    "inspect": "inspecting",
    "load": "loading",
    "read": "reading",
    "render": "rendering",
    "save": "saving",
    "traverse": "traversing",
    "use": "using",
    "work": "working",
    "write": "writing",
}


def _imported_python_types(code: str) -> list[str]:
    names: list[str] = []
    for imported in re.findall(r"(?m)^from\s+[\w.]+\s+import\s+([^\n]+)$", code):
        for raw in imported.split(","):
            name = raw.strip().split(" as ", 1)[0].strip()
            if re.fullmatch(r"[A-Z][A-Za-z0-9_]+", name) and name not in names:
                names.append(name)
    return names


def _semantic_title(code: str, language: str) -> str:
    normalized = " ".join(code.split())
    if "DisplayName" in code and re.search(r"\.Title\b|TitleText", code):
        return "Inspect document metadata and page titles"
    if re.search(r"(?i)Save\s*\([^)]*\.pdf|SaveFormat\.Pdf|PdfSaveOptions", code):
        return "Export a document to PDF"
    if "GetChildNodes(RichText" in normalized:
        return "Extract text from a document"
    if "GetChildNodes(Image" in normalized:
        return "Extract images from a document"
    if language.casefold() == "python":
        names = _imported_python_types(code)[:3]
        if names:
            rendered = (
                " and ".join(names)
                if len(names) < 3
                else ", ".join(names[:-1]) + f", and {names[-1]}"
            )
            return f"Explore the {rendered} APIs"
    return "Explore another repository workflow"


def public_example_title(
    source_title: str,
    code: str,
    language: str,
    used_heading_ids: set[str],
) -> str:
    """Return a meaningful, non-numbered heading unique within the README."""

    title = " ".join(source_title.split()).strip()
    title_id = heading_identity(title)
    if not title or title.casefold() in _GENERIC_TITLES or title_id in used_heading_ids:
        title = _semantic_title(code, language)
        title_id = heading_identity(title)
    if title_id in used_heading_ids:
        base = title
        qualifiers = [
            *_imported_python_types(code),
            *dict.fromkeys(
                match.group(1) for match in re.finditer(r"\b([a-z][a-z0-9_]{3,})\(", code)
            ),
            language.title(),
        ]
        for qualifier in qualifiers:
            title = f"{base} with {qualifier}"
            title_id = heading_identity(title)
            if title_id not in used_heading_ids:
                break
    if title_id in used_heading_ids:
        raise ValueError("additional examples require distinct visitor-facing workflow names")
    return title


def _gerund_phrase(title: str) -> str:
    words = title.split(maxsplit=1)
    if not words:
        return ""
    gerund = _ACTION_GERUNDS.get(words[0].casefold())
    if gerund is None:
        phrase = title[:1].lower() + title[1:]
    else:
        remainder = " ".join(
            word[:1].lower() + word[1:]
            if word[:1].isupper() and word[1:].islower() and len(word) > 3
            else word
            for word in (words[1].split() if len(words) == 2 else [])
        )
        phrase = f"{gerund} {remainder}".strip()
    for action, action_gerund in _ACTION_GERUNDS.items():
        phrase = re.sub(
            rf"(?i)\band\s+{re.escape(action)}\b",
            f"and {action_gerund}",
            phrase,
        )
    return phrase


def _preview_titles(titles: list[str], limit: int = 4) -> list[str]:
    selected: list[str] = []
    seen: set[tuple[str, str]] = set()
    for title in titles:
        words = re.findall(r"[a-z0-9]+", title.casefold())
        action = words[0] if words else ""
        target = (
            "pdf"
            if "pdf" in words
            else next(
                (
                    word
                    for word in words[1:]
                    if word
                    not in {
                        "a",
                        "all",
                        "an",
                        "document",
                        "documents",
                        "file",
                        "files",
                        "from",
                        "in",
                        "ms",
                        "one",
                        "the",
                        "to",
                    }
                ),
                "",
            )
        )
        key = (action, target)
        if key in seen:
            continue
        seen.add(key)
        selected.append(title)
        if len(selected) == limit:
            break
    return selected


def public_examples_introduction(
    titles: list[str],
    *,
    has_repository_files: bool,
    has_result_assets: bool,
) -> str:
    """Describe expandable content without exposing internal assurance state."""

    preview_titles = _preview_titles(titles)
    phrases = [_gerund_phrase(title) for title in preview_titles]
    merged_phrases: list[str] = []
    for phrase in phrases:
        head, separator, target = phrase.rpartition(" to ")
        if merged_phrases and separator:
            previous_head, previous_separator, previous_target = merged_phrases[-1].rpartition(
                " to "
            )
            if previous_separator and previous_head == head and " and " not in previous_target:
                merged_phrases[-1] = f"{head} to {previous_target} and {target}"
                continue
        merged_phrases.append(phrase)
    phrases = merged_phrases
    extras = len(titles) - len(preview_titles)
    if has_repository_files:
        phrases.append("browsing repository example files")
    if has_result_assets:
        phrases.append("viewing generated example results")
    if not phrases:
        return "Expand this section to browse additional repository examples."
    if len(phrases) == 1:
        rendered = phrases[0]
    else:
        rendered = ", ".join(phrases[:-1]) + f", and {phrases[-1]}"
    suffix = (
        f", plus {extras} more {'workflow' if extras == 1 else 'workflows'}" if extras > 0 else ""
    )
    return f"Expand this section to view examples for {rendered}{suffix}."


__all__ = ["public_example_title", "public_examples_introduction"]
