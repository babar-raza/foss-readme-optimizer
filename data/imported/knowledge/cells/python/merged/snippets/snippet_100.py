# Adapted from aspose.org: knowledge/cells/python/merged/snippets/snippet_100.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_all_create_sparklines():

    """

    Run all test cases for creating Excel files with sparklines.

    """

    print("\n" + "="*70)

    print("Test: Create Excel Files with Sparklines")

    print("="*70)

    

    test_create_line_sparklines()

    test_create_column_sparklines()

    test_create_win_loss_sparklines()

    test_create_multiple_sparkline_groups()

    test_create_sparkline_with_empty_cells()

    

    print("\n" + "="*70)

    print("All tests completed successfully!")

    print("="*70 + "\n")