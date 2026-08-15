# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_036.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_type2_invalid_subr_index():

    cs = b"".join([_enc_num(0), _enc_num(0), bytes([21]), _enc_num(0), bytes([10, 14])])

    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=0)

    with pytest.raises(FontParseException):

        interp.interpret(cs)