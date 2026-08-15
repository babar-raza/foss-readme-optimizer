# Adapted from aspose.org: knowledge/slides/python/merged/snippets/snippet_095.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

def test_plain_bubble_emits_bubble3D_val_0(self, tmp_path):

        """Plain bubble series also get an explicit <c:bubble3D val="0"/>."""

        pres = Presentation()

        chart = _add_clean_chart(pres, ChartType.BUBBLE)

        s = chart.chart_data.series.add("B", ChartType.BUBBLE)

        s.data_points.add_data_point_for_bubble_series(1.0, 2.0, 10)



        xml = self._save_and_read_chart_xml(pres, tmp_path)

        ser_block = xml.split('<c:ser>')[1].split('</c:ser>')[0]

        assert '<c:bubble3D val="0"/>' in ser_block