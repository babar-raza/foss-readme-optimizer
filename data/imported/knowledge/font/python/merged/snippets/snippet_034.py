# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_034.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_type2_width_extraction():

    # 50 is width; 0 0 rmoveto.

    cs = b"".join([_enc_num(50), _enc_num(0), _enc_num(0), bytes([21, 14])])

    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=400)

    _, width = interp.interpret(cs)

    assert width == 450