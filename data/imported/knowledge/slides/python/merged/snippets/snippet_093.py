# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_093.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_scatter_yVal_values_are_non_zero(self, tmp_path):

        """Regression: yVal used to emit zeros when y_value was set via the

        scatter API."""

        pres = Presentation()

        chart = _add_clean_chart(pres, ChartType.SCATTER_WITH_MARKERS)

        s = chart.chart_data.series.add("S", ChartType.SCATTER_WITH_MARKERS)

        s.data_points.add_data_point_for_scatter_series(1.0, 7.5)

        s.data_points.add_data_point_for_scatter_series(2.0, 8.5)



        xml = self._save_and_read_chart_xml(pres, tmp_path)

        yval_block = xml.split('<c:yVal>')[1].split('</c:yVal>')[0]

        assert '<c:v>7.5</c:v>' in yval_block

        assert '<c:v>8.5</c:v>' in yval_block