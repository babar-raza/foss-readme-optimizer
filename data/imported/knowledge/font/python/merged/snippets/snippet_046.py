# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_046.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_info_accepts_collection_index_for_ttc(tmp_path: Path):

    ttc_path = tmp_path / "sample.ttc"

    ttc_path.write_bytes(

        _build_ttc(

            _build_minimal_sfnt(b"\x00\x01\x00\x00"),

            _build_minimal_sfnt(b"OTTO"),

        )

    )



    result = run("info", str(ttc_path), "--collection-index", "1")



    assert result.returncode == 0

    assert "Format:      OTF" in result.stdout

    assert "Collection:  1/1" in result.stdout