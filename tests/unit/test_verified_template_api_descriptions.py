"""Visitor-facing Python API description composition regressions."""

from readme_agent.presentation.verified_template_api_descriptions import (
    describe_api_export,
    describe_api_member,
    member_api_identifier,
    namespace_display_name,
)


def _method(name: str) -> dict[str, object]:
    # A real, working method (this file's fixtures model genuine Aspose API
    # members) -- `implemented: True` is the honest production shape once
    # curated_python_api_projection.py has computed it, not a test-only
    # relaxation of the owner-review invariant that unknown must stay
    # conservative.
    return {"name": name, "kind": "method", "inherited": False, "implemented": True}


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


def test_generic_function_names_produce_concrete_source_bound_roles() -> None:
    cases = {
        ("aspose.words_foss", "loading"): "Groups public APIs for loading supported content.",
        ("aspose.words_foss", "saving"): "Groups public APIs for saving supported content.",
        ("aspose.words_foss.md_import", "drive_block"): (
            "Advances block-level parsing across Markdown source content."
        ),
        ("aspose.words_foss.md_import", "is_block_start"): (
            "Reports whether block start applies to the inspected content."
        ),
        ("aspose.words_foss.md_import", "parse_and_build"): (
            "Parses source content and builds the corresponding document structure."
        ),
        ("aspose.words_foss.md_import", "parse_document"): ("Parses document from source content."),
        ("aspose.words_foss.utils", "find_all_elements"): ("Finds all elements in source content."),
        ("aspose.words_foss.utils", "get_element_text"): (
            "Returns element text from source content."
        ),
        ("aspose.words_foss.docx_writer", "render_styles_xml"): (
            "Renders styles XML for serialized output."
        ),
    }

    for (module, name), expected in cases.items():
        assert describe_api_export(None, module=module, name=name, family="Words") == expected


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
        "implemented": True,
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


def test_spreadsheet_io_and_encryption_functions_have_concrete_descriptions() -> None:
    expectations = {
        "load_csv_workbook": "Loads CSV workbook from source content.",
        "save_workbook_as_csv": "Saves workbook content as CSV output.",
        "save_workbook_as_json": "Saves workbook content as JSON output.",
        "save_workbook_as_markdown": "Saves workbook content as Markdown output.",
        "encrypt_xlsx": "Encrypts XLSX content with the requested password and parameters.",
        "decrypt_xlsx": "Decrypts password-protected XLSX content.",
    }

    for name, expected in expectations.items():
        assert (
            describe_api_export(
                None,
                module="aspose.cells_foss",
                name=name,
                family="Cells",
            )
            == expected
        )


def test_barcode_generator_functions_have_concrete_symbology_descriptions() -> None:
    expectations = {
        "code128": "Generates a Code 128 barcode from the supplied content.",
        "code39": "Generates a Code 39 barcode from the supplied content.",
        "code39ext": "Generates an extended Code 39 barcode for full ASCII content.",
        "ean13": "Generates an EAN-13 retail barcode from numeric content.",
        "ean8": "Generates an EAN-8 retail barcode from numeric content.",
        "generate": "Selects a registered symbology and generates its barcode representation.",
        "qr": "Generates a QR Code symbol from the supplied content.",
        "upca": "Generates a UPC-A retail barcode from numeric content.",
        "upce": "Generates a zero-suppressed UPC-E retail barcode from numeric content.",
    }

    for name, expected in expectations.items():
        assert (
            describe_api_export(None, module="aspose_barcode_foss", name=name, family="Barcode")
            == expected
        )


def test_cfb_directory_name_comparison_has_a_concrete_description() -> None:
    assert (
        describe_api_export(
            None,
            module="aspose.email_foss.cfb",
            name="compare_directory_entry_names",
            family="Email",
        )
        == "Compares CFB directory-entry names using the format's ordering rules."
    )


def test_font_cryptography_and_preset_helpers_have_concrete_descriptions() -> None:
    expectations = {
        "available_subset_presets": (
            "Returns the subset presets available to font-processing workflows."
        ),
        "charstring_decrypt_full": "Decrypts a complete Type 1 charstring byte sequence.",
        "eexec_decrypt": "Decrypts Type 1 eexec-encrypted font data.",
        "eexec_encrypt": "Encrypts font data with the Type 1 eexec algorithm.",
    }

    for name, expected in expectations.items():
        assert describe_api_export(None, module="aspose_font", name=name, family="Font") == expected


def test_stub_method_is_discoverable_but_never_authorizes_capability_prose() -> None:
    """K2 mandatory red/green: `NurbsSurface.to_mesh` remains discoverable
    as a public signature, but its description must not use "supports,"
    "converts," or equivalent capability language while the method's cited
    body is a proven stub (`implemented is False`)."""

    stub_member = {
        "name": "to_mesh",
        "kind": "method",
        "surface": "to_mesh()",
        "declared_by": "NurbsSurface",
        "inherited": False,
        "implemented": False,
    }

    assert member_api_identifier("NurbsSurface", stub_member) == "NurbsSurface.to_mesh()"
    description = describe_api_member("NurbsSurface", stub_member)

    assert description == (
        "Declares the `to_mesh` operation on `NurbsSurface` (not yet implemented)."
    )
    lowered = description.casefold()
    assert "supports" not in lowered
    assert "converts" not in lowered
    assert "renders" not in lowered


def test_stub_method_never_contributes_a_supports_action_to_the_class_summary() -> None:
    """The class-level overview (`describe_api_export`'s "Supports ..."
    sentence) must skip a stub method entirely -- not merely soften its own
    per-member wording."""

    item = {
        "bases": [],
        "members": [
            {
                "name": "to_mesh",
                "kind": "method",
                "declared_by": "NurbsSurface",
                "inherited": False,
                "implemented": False,
            }
        ],
    }

    description = describe_api_export(
        item, module="aspose.threed", name="NurbsSurface", family="3D"
    )

    assert "supports" not in description.casefold()
    assert "mesh" not in description.casefold()


def test_unknown_implementation_method_never_contributes_a_supports_action_either() -> None:
    """Owner-review correction: an unresolved (`implemented` absent/`None`)
    method must be just as absent from the class summary's "Supports ..."
    sentence as a proven stub -- unknown is conservative, never optimistic."""

    item = {
        "bases": [],
        "members": [
            {
                "name": "to_mesh",
                "kind": "method",
                "declared_by": "NurbsSurface",
                "inherited": False,
            }
        ],
    }

    description = describe_api_export(
        item, module="aspose.threed", name="NurbsSurface", family="3D"
    )

    assert "supports" not in description.casefold()
    assert "mesh" not in description.casefold()


def test_only_proven_implemented_true_uses_capability_phrasing() -> None:
    """Owner-review correction: only a proven `implemented is True` may use
    capability wording. A missing/`None` `implemented` key (unresolvable --
    no evidence either way) is conservative, exactly like a proven `False`
    stub, but with its own neutral phrasing that asserts neither a
    capability nor a negative -- never "Supports ..." for either."""

    real_member = {
        "name": "to_mesh",
        "kind": "method",
        "declared_by": "NurbsSurface",
        "inherited": False,
        "implemented": True,
    }
    unknown_member = {
        "name": "to_mesh",
        "kind": "method",
        "declared_by": "NurbsSurface",
        "inherited": False,
    }

    assert describe_api_member("NurbsSurface", real_member) == (
        "Supports converting content to mesh through `NurbsSurface`."
    )
    unknown_description = describe_api_member("NurbsSurface", unknown_member)
    assert unknown_description == "Exposes the `to_mesh` operation on `NurbsSurface`."
    lowered = unknown_description.casefold()
    assert "supports" not in lowered
    assert "converts" not in lowered
    assert "not yet implemented" not in lowered


def test_supports_format_uses_a_grammatical_class_summary_phrase() -> None:
    item = {
        "bases": [],
        "members": [
            {
                "name": "supports_format",
                "kind": "method",
                "declared_by": "Exporter",
                "inherited": False,
                "implemented": True,
            }
        ],
    }

    description = describe_api_export(item, module="aspose.threed", name="Exporter", family="3D")

    assert description.endswith("Supports checking format support.")
    assert "supportsing" not in description


def test_scalar_returning_from_method_is_not_described_as_loading_content() -> None:
    """PWD-008, live on aspose-words-foss: `ImageData.from_mime(mime: str) -> int` -- real,
    verified against the actual source -- maps a MIME string to an `ImageType` constant; it
    never loads or returns content. The name-only "from X" heuristic wrongly produced "Supports
    loading content from MIME", tripping the format-direction linter on a phantom input claim.
    A bare scalar return type (int/bool/float) can never be "loaded content"."""

    member = {
        "name": "from_mime",
        "kind": "method",
        "surface": "from_mime(mime)",
        "return_annotation": "int",
        "declared_by": "ImageData",
        "inherited": False,
        "implemented": True,
    }

    per_member_description = describe_api_member("ImageData", member)
    class_summary = describe_api_export(
        {"bases": ["BaseModel"], "members": [member]},
        module="aspose.words_foss.drawing",
        name="ImageData",
        family="Words",
    )

    assert per_member_description == "Calls the `from_mime` operation on `ImageData`."
    assert "loading content" not in per_member_description.casefold()
    assert "mime" not in class_summary.casefold()
    assert "loading content" not in class_summary.casefold()


def test_content_returning_from_method_still_describes_loading_content() -> None:
    """Negative control: a genuine content-loading "FromX" constructor -- unspecified or
    non-scalar return type -- must still get its "Supports loading content from ..." phrase;
    the fix narrows only the scalar-return case, never the general one."""

    member = {
        "name": "from_docx",
        "kind": "method",
        "surface": "from_docx(path)",
        "return_annotation": "Document",
        "declared_by": "Document",
        "inherited": False,
        "implemented": True,
    }

    assert describe_api_member("Document", member) == (
        "Supports loading content from DOCX through `Document`."
    )

    no_annotation_member = {**member, "return_annotation": None}
    assert describe_api_member("Document", no_annotation_member) == (
        "Supports loading content from DOCX through `Document`."
    )
