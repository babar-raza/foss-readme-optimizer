"""Normalize visitor-facing Python API names, grammar, and namespace labels."""

from __future__ import annotations

import re

from readme_agent.readme.public_text import canonicalize_abbreviations

_ROLE_SUFFIXES = (
    ("SaveOptions", "Configures {subject} output"),
    ("Options", "Configures {subject} operations"),
    ("Document", "Represents {article} {subject} document"),
    ("Renderer", "Renders {subject} content"),
    ("Writer", "Writes {subject} output"),
    ("Reader", "Reads {subject} content"),
    ("Converter", "Converts {subject} content"),
    ("Builder", "Builds {subject}"),
    ("Metadata", "Stores {subject} metadata"),
    ("Resource", "Stores {subject} resource data"),
    ("Command", "Represents {article} {subject} command"),
    ("Result", "Stores {subject} result data"),
    ("Input", "Defines {subject} input"),
    ("Output", "Defines {subject} output"),
    ("Canvas", "Provides {article} {subject} drawing canvas"),
    ("State", "Stores {subject} state"),
    ("Font", "Represents {article} {subject} font"),
    ("Path", "Represents {article} {subject} path"),
)


def split_identifier_words(value: str) -> list[str]:
    """Split snake-case and CamelCase identifiers without changing the identifier itself."""

    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    expanded = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", expanded).replace("_", " ")
    return expanded.split()


def public_noun(value: str) -> str:
    """Render an identifier as canonical visitor-facing terminology."""

    rendered = canonicalize_abbreviations(" ".join(split_identifier_words(value)))
    replacements = (
        (r"\bXmp\b", "XMP"),
        (r"\bUri\b", "URI"),
        (r"\bAspose PDF\b", "Aspose.PDF"),
        (r"\bPDF A\b", "PDF/A"),
        (r"\bPDF UA\b", "PDF/UA"),
        (r"\bMatrix 3 D\b", "Matrix3D"),
        (r"\bMatrix3 D\b", "Matrix3D"),
        (r"\bPoint 3 D\b", "Point3D"),
        (r"\bPoint3 D\b", "Point3D"),
        (r"\bMs One Note\b", "Microsoft OneNote"),
        (r"\bStl\b", "STL"),
        (r"\bThreemf\b", "3MF"),
    )
    for pattern, replacement in replacements:
        rendered = re.sub(pattern, replacement, rendered, flags=re.IGNORECASE)
    return rendered


def human_name(value: str) -> str:
    """Return a normalized lower-case visitor phrase for an identifier."""

    return public_noun(value).casefold()


def brand_name(value: str) -> str:
    """Return a product-family token with canonical technical casing."""

    public = public_noun(value)
    return public[:1].upper() + public[1:]


def grammatical_article(value: str) -> str:
    """Choose an indefinite article for a public API noun."""

    first_token = re.split(r"[\s/.-]+", value.strip(), maxsplit=1)[0]
    if first_token.upper() in {"URI", "URL", "UUID"}:
        return "a"
    if first_token.isupper() and first_token[:1] in {
        "A",
        "E",
        "F",
        "H",
        "I",
        "L",
        "M",
        "N",
        "O",
        "R",
        "S",
        "X",
    }:
        return "an"
    return "an" if value[:1].casefold() in {"a", "e", "i", "o", "u"} else "a"


def series(items: list[str]) -> str:
    """Join public phrases with an Oxford comma."""

    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def role_sentence(name: str, module: str, family: str) -> str:
    """Describe the stable role implied by a public type name."""

    public_name = public_noun(name)
    public_family = f"Aspose.{brand_name(family)}" if family else "the package"
    for suffix, template in _ROLE_SUFFIXES:
        if not name.endswith(suffix):
            continue
        subject = public_noun(name.removesuffix(suffix)).strip() or public_noun(family)
        subject = re.sub(r"\b(?:Validate|Validation)\b", "validation", subject)
        return (
            template.format(subject=subject, article=grammatical_article(subject))
            + f" through the {public_family} API."
        )
    if module.casefold() in {
        "aspose",
        f"aspose.{family}".casefold(),
        f"aspose_{family}".casefold(),
    }:
        return (
            f"Represents {grammatical_article(public_name)} {public_name} "
            f"in the public {public_family} API."
        )
    domain = canonicalize_abbreviations(module.rsplit(".", 1)[-1].replace("_", " "))
    return (
        f"Represents {grammatical_article(public_name)} {public_name} in the public {domain} API "
        f"for {public_family}."
    )


def namespace_display_name(module: str, family: str) -> str:
    """Brand a namespace heading while retaining its exact identifier separately."""

    def display_part(value: str) -> str:
        if "_" not in value and any(character.isupper() for character in value[1:]):
            return canonicalize_abbreviations(value)
        words = [word[:1].upper() + word[1:] for word in value.split("_") if word]
        return public_noun(" ".join(words))

    parts = module.split(".")
    rendered_parts: list[str] = []
    first = parts[0]
    start = 1
    if first.casefold() == "aspose":
        rendered_parts.append("Aspose")
        if len(parts) > 1:
            rendered_parts.append(display_part(family or parts[1]))
            start = 2
    elif first.casefold().startswith("aspose_"):
        suffix = first[len("aspose_") :]
        rendered_parts.extend(["Aspose", display_part(family or suffix)])
    else:
        rendered_parts.append(display_part(first))
    rendered_parts.extend(display_part(part) for part in parts[start:])
    return ".".join(rendered_parts)


__all__ = [
    "brand_name",
    "grammatical_article",
    "human_name",
    "namespace_display_name",
    "public_noun",
    "role_sentence",
    "series",
    "split_identifier_words",
]
