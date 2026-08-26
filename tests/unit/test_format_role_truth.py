"""Document-format role recognition regressions."""

from readme_agent.readme.format_role_truth import mentioned_document_formats


def test_ordinary_lowercase_one_is_not_a_onenote_format() -> None:
    assert mentioned_document_formats("Export workbooks into one cloneable value") == set()


def test_explicit_one_format_forms_remain_recognized() -> None:
    assert mentioned_document_formats("Read ONE files and save a .one document") == {"ONE"}
