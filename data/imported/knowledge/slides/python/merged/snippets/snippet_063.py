# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_063.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_axis_fill_format(self):

        prs = Presentation()

        chart = prs.slides[0].shapes.add_chart(ChartType.CLUSTERED_COLUMN, 0, 0, 400, 300)

        fmt = chart.axes.vertical_axis.format

        fmt.fill.fill_type = FillType.SOLID

        fmt.fill.solid_fill_color.color = Color.from_argb(255, 200, 200, 200)



        prs2 = _save_and_reload(prs)

        chart2 = prs2.slides[0].shapes[0]

        fmt2 = chart2.axes.vertical_axis.format

        assert fmt2.fill.fill_type == FillType.SOLID

        assert fmt2.fill.solid_fill_color.color.r == 200