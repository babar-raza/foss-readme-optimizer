# Adapted from aspose.org: knowledge/page/python/merged/snippets/snippet_007.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_opposite_winding_contours_keep_nonzero(self) -> None:

        contours = [

            _cw_square(0, 0, 1000, 1000),

            _ccw_square(250, 250, 750, 750),

        ]

        self.assertFalse(_glyph_contours_need_even_odd(contours))