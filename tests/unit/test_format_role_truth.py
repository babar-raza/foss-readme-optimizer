"""Document-format role recognition regressions."""

from readme_agent.readme.format_role_truth import formats_in_api_symbol, mentioned_document_formats


def test_ordinary_lowercase_one_is_not_a_onenote_format() -> None:
    assert mentioned_document_formats("Export workbooks into one cloneable value") == set()


def test_explicit_one_format_forms_remain_recognized() -> None:
    assert mentioned_document_formats("Read ONE files and save a .one document") == {"ONE"}


def test_emphatic_uppercase_one_is_not_a_onenote_format() -> None:
    """PWD-008: live aspose-page-foss finding -- prose emphasis ("exactly ONE input",

    "instantiating ONE public API object") writes the ordinary number word in the same
    all-caps form the ONE (OneNote) format code uses. Case alone can't disambiguate this;
    only a trailing file/format noun (the true positive below) can.
    """

    assert mentioned_document_formats("Exponential functions require exactly ONE input.") == set()
    assert (
        mentioned_document_formats(
            "instantiating ONE public API object in Python to provide a first glimpse"
        )
        == set()
    )


def test_ordinary_lowercase_one_is_not_a_onenote_api_symbol() -> None:
    assert formats_in_api_symbol("one") == set()


def test_explicit_one_api_symbol_remains_recognized() -> None:
    assert formats_in_api_symbol("ONE") == {"ONE"}
