"""Prove public constraint text rejects internal diagnostics without hiding limitations."""

from readme_agent.facts.public_constraint_text import is_public_constraint_sentence


def test_public_constraint_text_accepts_visitor_facing_limitations() -> None:
    assert is_public_constraint_sentence("Password-protected documents are not supported")
    assert is_public_constraint_sentence("Only PDF save output is supported")
    assert is_public_constraint_sentence(
        "Live DOM lookup for the referenced datalist is not implemented"
    )


def test_public_constraint_text_rejects_internal_or_malformed_diagnostics() -> None:
    assert not is_public_constraint_sentence("is not implemented (out of scope for Level 3)")
    assert not is_public_constraint_sentence(
        "Returns ------- CSSRule Raises ------ SyntaxError for unsupported rule syntax"
    )
    assert not is_public_constraint_sentence("document attach requires replacing_document state")
    assert not is_public_constraint_sentence("navigation completion requires parsing state")
    assert not is_public_constraint_sentence("Unsupported complex structures (e.g.")
