# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_079.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_add_scatter_data_points(self):

        """X/Y values are accessible on the data points after adding."""

        pres = Presentation()

        chart = _add_clean_chart(pres, ChartType.SCATTER_WITH_MARKERS)

        s = chart.chart_data.series.add("S", ChartType.SCATTER_WITH_MARKERS)

        pts = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]

        for x, y in pts:

            s.data_points.add_data_point_for_scatter_series(x, y)



        assert len(s.data_points) == 3

        for dp, (x, y) in zip(s.data_points, pts):

            assert dp.x_value.as_literal_double == x

            assert dp.y_value.as_literal_double == y