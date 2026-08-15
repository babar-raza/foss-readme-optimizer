# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_040.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_clean_for_web_keep_flags_preserve_requested_metadata(roboto_path: Path):

    font = _font_with_extra_metadata(roboto_path)



    cleaned = FontCleaner.clean_for_web(

        font,

        drop_mac_names=False,

        drop_legacy_tables=False,

        drop_metadata_tables=False,

    )



    assert "DSIG" in cleaned.ttf_tables._raw

    assert "FFTM" in cleaned.ttf_tables._raw

    assert "meta" in cleaned.ttf_tables._raw

    assert cleaned.ttf_tables.name is not None

    assert any(record.platform_id == 1 for record in cleaned.ttf_tables.name.records)