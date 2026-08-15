# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_008.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_prescan_limit_1024():

    # <meta charset> appears at byte 1025 — must NOT be detected.

    padding = b" " * 1024

    data = padding + b'<meta charset="windows-1252">'

    assert prescan_meta_charset(data) is None