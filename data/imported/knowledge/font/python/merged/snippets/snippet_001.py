# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_001.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_encode_apng_from_rgb():

    w, h = 10, 10

    frame1 = bytearray([255, 0, 0] * w * h)

    frame2 = bytearray([0, 255, 0] * w * h)



    apng = encode_apng_from_rgb([bytes(frame1), bytes(frame2)], w, h, fps=10)



    # Check signature

    assert apng.startswith(b"\x89PNG\r\n\x1a\n")

    # Verify animation chunks exist

    assert b"acTL" in apng

    assert b"fcTL" in apng

    assert b"fdAT" in apng

    # Standard PNG endings

    assert apng.endswith(b"IEND\xaeB`\x82")