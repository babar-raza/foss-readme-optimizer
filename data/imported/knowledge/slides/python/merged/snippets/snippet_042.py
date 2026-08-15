# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_042.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_get_or_create_by_value_custom(self):

        bp = anim.BehaviorProperty()

        result = bp.get_or_create_by_value('my.custom.prop')

        assert result.value == 'my.custom.prop'

        assert result.is_custom is True