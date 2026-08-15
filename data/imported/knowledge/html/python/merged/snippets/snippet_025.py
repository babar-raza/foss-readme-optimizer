# Adapted from aspose.org: knowledge/html/python/merged/snippets/snippet_025.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_smoke_all_codecs(canonical_name: str):

    payload = _SMOKE_PAYLOADS.get(canonical_name, b"Hello")

    text, errors = decode_bytes(payload, canonical_name)

    assert isinstance(text, str)

    # No unexpected exception raised.
