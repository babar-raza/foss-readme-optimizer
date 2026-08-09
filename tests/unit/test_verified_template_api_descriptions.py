"""Visitor-facing Python API description composition regressions."""

from readme_agent.presentation.verified_template_api_descriptions import (
    describe_api_export,
    describe_api_member,
    member_api_identifier,
    namespace_display_name,
)


def _method(name: str) -> dict[str, object]:
    return {"name": name, "kind": "method", "inherited": False}


def test_document_description_uses_role_and_complete_member_actions() -> None:
    item = {
        "bases": [],
        "members": [_method("add_page"), _method("as_bytes"), _method("create")],
    }

    description = describe_api_export(
        item,
        module="aspose.page.ps",
        name="PsDocument",
        family="page",
    )

    assert description == (
        "Represents a PS document through the Aspose.Page API. Supports adding pages, "
        "serializing content to bytes, and creating document instances."
    )
    assert "verified" not in description.casefold()
    assert ": add," not in description.casefold()


def test_function_descriptions_explain_concrete_behavior() -> None:
    assert (
        describe_api_export(
            None,
            module="aspose.page.mcp",
            name="create_server",
            family="page",
        )
        == "Creates and configures the Aspose.Page MCP server."
    )
    assert (
        describe_api_export(
            None,
            module="aspose.note.saving.pdf_writer",
            name="write_pdf",
            family="note",
        )
        == "Writes PDF output through the public Aspose.Note API."
    )
    assert (
        describe_api_export(
            None,
            module="aspose.page.mcp.handlers",
            name="ps_to_pdf",
            family="page",
        )
        == "Converts PS content to PDF output."
    )
    assert (
        describe_api_export(
            None,
            module="aspose.page.image.encoders",
            name="encode_png",
            family="page",
        )
        == "Encodes raster data as PNG output."
    )


def test_namespace_display_is_branded_but_import_identifier_can_remain_exact() -> None:
    assert namespace_display_name("aspose.page.pdf.writer", "page") == "Aspose.Page.PDF.Writer"
    assert namespace_display_name("aspose.threed.formats.stl", "3D") == ("Aspose.3D.Formats.STL")
    assert namespace_display_name("aspose.threed.formats.threemf", "3D") == (
        "Aspose.3D.Formats.3MF"
    )


def test_missing_class_projection_uses_type_role_instead_of_function_fallback() -> None:
    assert (
        describe_api_export(
            None,
            module="aspose.page.pdf",
            name="PdfWriter",
            family="page",
        )
        == "Writes PDF output through the Aspose.Page API."
    )
    assert (
        describe_api_export(
            None,
            module="aspose.page.xps",
            name="XpsDocument",
            family="page",
        )
        == "Represents an XPS document through the Aspose.Page API."
    )


def test_generated_exports_and_xmp_functions_have_visitor_roles() -> None:
    assert (
        describe_api_export(
            None,
            module="aspose_pdf",
            name="parse_xmp",
            family="PDF",
        )
        == "Parses XMP metadata from source content."
    )
    assert (
        describe_api_export(
            None,
            module="aspose_pdf.generated",
            name="annotations",
            family="PDF",
        )
        == "Exposes generated annotations compatibility definitions."
    )


def test_member_grammar_handles_predicates_conversion_and_irregular_plurals() -> None:
    item = {
        "bases": [],
        "members": [_method("is_byte_array"), _method("to_dict"), _method("add_checkbox")],
    }

    description = describe_api_export(
        item,
        module="aspose_pdf",
        name="OperationResult",
        family="PDF",
    )

    assert "checking for byte-array results" in description
    assert "serializing values to a dictionary" in description
    assert "adding checkboxes" in description


def test_public_descriptions_preserve_canonical_pdf_and_3d_terminology() -> None:
    exception = describe_api_export(
        {"bases": ["Exception"], "members": []},
        module="aspose_pdf",
        name="AsposePdfException",
        family="PDF",
    )
    assert exception == "Signals an Aspose.PDF condition; derives from `Exception`."

    assert "PDF/UA" in describe_api_export(
        None,
        module="aspose_pdf",
        name="PdfUaValidationMode",
        family="PDF",
    )
    assert "Matrix3D" in describe_api_export(
        None,
        module="aspose_pdf",
        name="Matrix3D",
        family="PDF",
    )
    assert "PDF/A validation" in describe_api_export(
        {"bases": [], "members": []},
        module="aspose_pdf",
        name="PdfAValidateOptions",
        family="PDF",
    )
    assert "PDF/UA validation" in describe_api_export(
        {"bases": [], "members": []},
        module="aspose_pdf",
        name="PdfUaValidationResult",
        family="PDF",
    )
    assert describe_api_export(
        {"bases": ["Action"], "members": []},
        module="aspose_pdf",
        name="URIAction",
        family="PDF",
    ).startswith("Represents a URI Action")


def test_constants_articles_and_member_fragments_are_visitor_safe() -> None:
    assert (
        describe_api_export(
            None,
            module="aspose_pdf",
            name="AF_RELATIONSHIPS",
            family="PDF",
        )
        == "Defines the `AF_RELATIONSHIPS` public constant."
    )

    packet = describe_api_export(
        {"bases": [], "members": [_method("has_packet"), {"name": "Childs", "kind": "property"}]},
        module="aspose_pdf.xmp",
        name="XmpPacket",
        family="PDF",
    )
    assert "an XMP Packet" in packet
    assert "checking for packet" in packet
    assert "childs" not in packet.casefold()


def test_every_member_has_an_exact_class_qualified_surface_and_complete_description() -> None:
    method = {
        "name": "copy_to",
        "kind": "method",
        "surface": "copy_to(target, start_index=0)",
        "return_annotation": "None",
        "declared_by": "NodeCollection",
        "inherited": False,
    }
    assert member_api_identifier("NodeCollection", method) == (
        "NodeCollection.copy_to(target, start_index=0) -> None"
    )
    assert describe_api_member("NodeCollection", method) == (
        "Supports copying the current value to a destination through `NodeCollection`."
    )

    enum_member = {
        "name": "MS_ONE_NOTE",
        "kind": "enum_member",
        "surface": "MS_ONE_NOTE",
        "declared_by": "FileFormat",
        "inherited": False,
    }
    assert member_api_identifier("FileFormat", enum_member) == "FileFormat.MS_ONE_NOTE"
    assert describe_api_member("FileFormat", enum_member) == (
        "Selects the `MS_ONE_NOTE` value from the `FileFormat` enumeration."
    )


def test_fragmentary_member_names_fall_back_to_exact_identifiers() -> None:
    member = {
        "name": "descendants_cannot_be_moved",
        "kind": "property",
        "surface": "descendants_cannot_be_moved: bool",
        "declared_by": "OutlineElement",
        "inherited": False,
    }

    description = describe_api_member("OutlineElement", member)

    assert description == ("Gets the `descendants_cannot_be_moved` property on `OutlineElement`.")
    assert "descendants cannot be moved" not in description


def test_visitor_start_and_end_callbacks_have_distinct_complete_descriptions() -> None:
    start = _method("VisitPageStart")
    end = _method("VisitPageEnd")

    assert describe_api_member("DocumentVisitor", start) == (
        "Supports starting a visit to page through `DocumentVisitor`."
    )
    assert describe_api_member("DocumentVisitor", end) == (
        "Supports finishing a visit to page through `DocumentVisitor`."
    )


def test_class_summary_never_hides_an_opaque_additional_member_count() -> None:
    item = {
        "bases": [],
        "members": [_method("save"), _method("load"), _method("clone"), _method("clear")],
    }

    description = describe_api_export(
        item,
        module="aspose.note",
        name="Document",
        family="note",
    )

    assert "additional member" not in description.casefold()


def test_case_variant_member_descriptions_remain_distinct_and_fact_bound() -> None:
    member = {"name": "Delete", "kind": "method", "inherited": False}

    assert describe_api_member("PageCollection", member, case_variant_of="delete") == (
        "Exposes the `Delete` entry point alongside `delete` on `PageCollection`."
    )
