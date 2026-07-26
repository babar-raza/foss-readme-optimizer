"""Normalizes model-authored source text before deterministic compilation."""

from __future__ import annotations

_TYPOGRAPHIC_QUOTES = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u00ab": '"',
        "\u00bb": '"',
    }
)


def normalize_generated_code(source: str) -> str:
    """Replace typographic quote delimiters with parser-safe ASCII quotes.

    Model gateways can return visually correct smart quotes in otherwise
    valid source. Normalization does not establish correctness: the exact
    normalized source still has to pass the ecosystem compiler or executor.
    """

    return source.translate(_TYPOGRAPHIC_QUOTES)
