# Adapted from aspose.org: knowledge/font/python/merged/snippets/snippet_038.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_type2_stack_limit():

    cs = (bytes([139]) * 514) + bytes([14])

    interp = Type2Interpreter(CffIndex([]), CffIndex([]), default_width_x=500, nominal_width_x=0)

    with pytest.raises(FontParseException):

        interp.interpret(cs)