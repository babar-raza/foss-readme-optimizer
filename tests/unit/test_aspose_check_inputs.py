from readme_agent.validation.aspose_check_inputs import qualified_check_inputs


def test_format_casing_input_omits_badge_alt_text_but_preserves_prose():
    candidate = (
        "# Product for .NET\n\n"
        "[![Contributors: example-net/Product-for-NET]"
        "(https://img.shields.io/badge/contributors)](https://example.invalid)\n\n"
        "The .NET library reads PDF documents.\n"
    )

    adapted = qualified_check_inputs(
        "check_format_name_casing",
        {"readme_text": candidate, "markdown_text": candidate},
    )

    assert "example-net" not in adapted["readme_text"]
    assert "The .NET library reads PDF documents." in adapted["readme_text"]
    assert adapted["markdown_text"] == candidate


def test_unrelated_check_receives_the_original_input_mapping():
    available = {"readme_text": "![Format: pdf](badge) PDF"}

    assert qualified_check_inputs("check_heading_title_case", available) is available
