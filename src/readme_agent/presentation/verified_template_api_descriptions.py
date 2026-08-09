"""Compose visitor-facing descriptions from verified Python API surfaces."""

from __future__ import annotations

from typing import Any

from readme_agent.presentation.verified_template_api_members import (
    describe_api_member,
    member_api_identifier,
    summarize_api_members,
)
from readme_agent.presentation.verified_template_api_text import (
    brand_name,
    grammatical_article,
    human_name,
    namespace_display_name,
    public_noun,
    role_sentence,
    series,
    split_identifier_words,
)
from readme_agent.readme.public_text import canonicalize_abbreviations


def describe_api_export(
    item: dict[str, Any] | None,
    *,
    module: str,
    name: str,
    family: str,
) -> str:
    """Describe one accepted export without exposing internal assurance narration."""

    if name[:1].islower():
        return _function_description(name, module=module, family=family)
    if name.isupper() and "_" in name:
        return f"Defines the `{name}` public constant."
    if item is None:
        return role_sentence(name, module, family)
    bases = [str(base).strip() for base in item.get("bases", []) if str(base).strip()]
    if name.endswith("Exception") or any(base.endswith("Exception") for base in bases):
        condition = public_noun(name.removesuffix("Exception")).replace(" File Format", " format")
        if not condition.startswith("Aspose."):
            condition = " ".join(
                word if word.isupper() and len(word) > 1 else word.casefold()
                for word in condition.split()
            )
        inheritance = f"; derives from `{bases[0]}`" if bases else ""
        sentence = f"Signals {grammatical_article(condition)} {condition} condition{inheritance}."
        if len(sentence.rstrip(".")) < 24:
            sentence = (
                f"Signals {grammatical_article(condition)} {condition} error condition "
                f"raised by the public API{inheritance}."
            )
        return sentence
    if module.endswith(".enums") or any(base in {"Enum", "IntEnum", "StrEnum"} for base in bases):
        return f"Enumerates {human_name(name)} values."
    actions = summarize_api_members(item)
    sentences = [role_sentence(name, module, family)]
    if actions:
        sentences.append(f"Supports {series(actions)}.")
    if bases:
        sentences.append("Inherits from " + ", ".join(f"`{base}`" for base in bases) + ".")
    return " ".join(sentences)


def _function_description(name: str, *, module: str, family: str) -> str:
    words = [word.casefold() for word in split_identifier_words(name)]
    public_family = f"Aspose.{brand_name(family)}" if family else "the package"
    if name == "create_server":
        return f"Creates and configures the {public_family} MCP server."
    if name == "run" and (module.endswith(".mcp") or module.endswith(".server")):
        return f"Starts the {public_family} MCP server."
    if name == "rect_path":
        return "Creates a rectangular rendering path."
    if name == "skia_available":
        return "Reports whether the Skia raster backend is available."
    if name == "parse_xmp":
        return "Parses XMP metadata from source content."
    if name == "serialize_xmp":
        return "Serializes XMP metadata for PDF output."
    if module.endswith(".generated") and len(words) == 1:
        noun = canonicalize_abbreviations(words[0])
        return f"Exposes generated {noun} compatibility definitions."
    if len(words) == 2 and words[1] == "metadata":
        source = canonicalize_abbreviations(words[0])
        return f"Reads {source} metadata from source content."
    if len(words) >= 3 and "to" in words:
        split = words.index("to")
        source_words = words[1:split] if words[0] == "convert" else words[:split]
        source = canonicalize_abbreviations(" ".join(source_words))
        target = canonicalize_abbreviations(" ".join(words[split + 1 :]))
        return f"Converts {source} content to {target} output."
    verb = words[0] if words else ""
    remainder = canonicalize_abbreviations(" ".join(words[1:]))
    if verb == "encode" and remainder:
        return f"Encodes raster data as {remainder} output."
    if verb == "add" and remainder:
        return f"Adds {remainder} metadata to generated output."
    if verb == "build" and remainder:
        return f"Builds {remainder} data for generated output."
    if verb == "escape" and remainder:
        return f"Escapes {remainder} content for safe serialization."
    if verb == "format" and remainder:
        return f"Formats {remainder} values for serialized output."
    if verb == "select" and remainder:
        return f"Selects the appropriate {remainder} for the requested output."
    if verb == "write" and remainder:
        return f"Writes {remainder} output through the public {public_family} API."
    if verb in {"read", "extract"} and remainder:
        return f"{verb.capitalize()}s {remainder} from source content."
    if verb in {"create", "make"} and remainder:
        return f"Creates {remainder} objects for use with the public {public_family} API."
    action = public_noun(name).casefold()
    return f"Provides the {action} operation in the public {public_family} API."


__all__ = [
    "describe_api_export",
    "describe_api_member",
    "member_api_identifier",
    "namespace_display_name",
]
