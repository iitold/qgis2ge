"""Automated headless tests for qgis2ge export and updater logic.

Runs without GUI using PyQGIS.
"""

from __future__ import annotations

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from qgis.core import (
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsFillSymbol,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsProject,
    QgsProperty,
    QgsRendererCategory,
    QgsRendererRange,
    QgsRuleBasedRenderer,
    QgsSimpleFillSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from qgis2ge.exporter import (
    ExportOptions,
    export_kml,
    qcolor_to_kml_hex,
)


class DummyFeedback:
    def __init__(self, cancel_after: int = -1):
        self.progress = 0
        self.calls = 0
        self.cancel_after = cancel_after

    def setProgress(self, val: int):
        self.progress = val

    def isCanceled(self) -> bool:
        self.calls += 1
        if self.cancel_after >= 0 and self.calls >= self.cancel_after:
            return True
        return False


class TestQgis2GeExporter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qgs = QgsApplication([], False)
        cls.qgs.initQgis()
        cls.test_dir = tempfile.mkdtemp(prefix="qgis2ge_test_")

    @classmethod
    def tearDownClass(cls):
        import shutil

        cls.qgs.exitQgis()
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_qcolor_to_kml_hex(self):
        # Pure red opaque #ff0000 -> aabbggrr = ff 00 00 ff
        self.assertEqual(qcolor_to_kml_hex(255, 0, 0, 255), "ff0000ff")
        # Pure green opaque #00ff00 -> aabbggrr = ff 00 ff 00
        self.assertEqual(qcolor_to_kml_hex(0, 255, 0, 255), "ff00ff00")
        # Pure blue opaque #0000ff -> aabbggrr = ff ff 00 00
        self.assertEqual(qcolor_to_kml_hex(0, 0, 255, 255), "ffff0000")
        # Semi-transparent red (alpha=128 = 0x80)
        self.assertEqual(qcolor_to_kml_hex(255, 0, 0, 128), "800000ff")

    def test_single_symbol_and_stroke_modes(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=id:int&field=name:string", "poly_layer", "memory")
        dp = layer.dataProvider()

        f = QgsFeature(layer.fields())
        f.setAttributes([1, "Sector A"])
        f.setGeometry(QgsGeometry.fromWkt("POLYGON((106.0 10.0, 107.0 10.0, 107.0 11.0, 106.0 11.0, 106.0 10.0))"))
        dp.addFeatures([f])

        # Symbol: fill red (alpha 200), stroke black
        sym = QgsFillSymbol.createSimple({
            "color": "255,0,0,200",
            "outline_color": "0,0,0,255",
            "outline_width": "0.5",
        })
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

        # Test mode 'same': stroke should match fill color and alpha
        out_path = os.path.join(self.test_dir, "test_same.kml")
        opts = ExportOptions(out_path=out_path, stroke_mode="same")
        res = export_kml(layer, opts)

        self.assertEqual(res.exported_count, 1)
        self.assertEqual(res.skipped_count, 0)
        self.assertTrue(os.path.exists(out_path))

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        placemarks = root.findall(".//kml:Placemark", ns)
        self.assertEqual(len(placemarks), 1)

        # Style check
        styles = root.findall(".//kml:Style", ns)
        self.assertEqual(len(styles), 1)
        line_color = styles[0].find(".//kml:LineStyle/kml:color", ns).text
        poly_color = styles[0].find(".//kml:PolyStyle/kml:color", ns).text
        self.assertEqual(line_color, poly_color)
        self.assertEqual(poly_color, "c80000ff")  # 200 alpha = 0xc8

        # Test mode 'none': outline should be 0
        out_path_none = os.path.join(self.test_dir, "test_none.kml")
        opts_none = ExportOptions(out_path=out_path_none, stroke_mode="none")
        export_kml(layer, opts_none)
        tree_none = ET.parse(out_path_none)
        root_none = tree_none.getroot()
        outline_val = root_none.find(".//kml:PolyStyle/kml:outline", ns).text
        self.assertEqual(outline_val, "0")

    def test_categorized_renderer_and_deduplication(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=site:string&field=band:string", "sectors", "memory")
        dp = layer.dataProvider()

        feats = []
        for i, band in enumerate(["LTE1800", "LTE2100", "LTE1800", "LTE2600"]):
            f = QgsFeature(layer.fields())
            f.setAttributes([f"Site_{i}", band])
            f.setGeometry(QgsGeometry.fromWkt(f"POLYGON(({106+i} 10, {107+i} 10, {107+i} 11, {106+i} 11, {106+i} 10))"))
            feats.append(f)
        dp.addFeatures(feats)

        # Categorized renderer with 3 bands
        categories = [
            QgsRendererCategory("LTE1800", QgsFillSymbol.createSimple({"color": "255,0,0,255"}), "Band 1800"),
            QgsRendererCategory("LTE2100", QgsFillSymbol.createSimple({"color": "0,255,0,255"}), "Band 2100"),
            QgsRendererCategory("LTE2600", QgsFillSymbol.createSimple({"color": "0,0,255,255"}), "Band 2600"),
        ]
        renderer = QgsCategorizedSymbolRenderer("band", categories)
        layer.setRenderer(renderer)

        out_path = os.path.join(self.test_dir, "test_cat.kml")
        opts = ExportOptions(
            out_path=out_path,
            name_field="site",
            extra_fields=["band"],
            group_by_category=True,
        )
        res = export_kml(layer, opts)

        self.assertEqual(res.exported_count, 4)
        self.assertEqual(res.skipped_count, 0)

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        # Check deduplication: 4 features across 3 categories -> exactly 3 styles!
        styles = root.findall(".//kml:Style", ns)
        self.assertEqual(len(styles), 3)

        # Check Folders: 3 folders
        folders = root.findall(".//kml:Folder", ns)
        self.assertEqual(len(folders), 3)
        folder_names = [f.find("kml:name", ns).text for f in folders]
        self.assertIn("Band 1800", folder_names)
        self.assertIn("Band 2100", folder_names)
        self.assertIn("Band 2600", folder_names)

        # Check ExtendedData
        data_nodes = root.findall(".//kml:ExtendedData/kml:Data", ns)
        self.assertEqual(len(data_nodes), 4)
        self.assertEqual(data_nodes[0].get("name"), "band")

    def test_polygon_with_holes_and_multipolygon(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=id:int", "geom_test", "memory")
        dp = layer.dataProvider()

        # Feature 1: polygon with hole
        f1 = QgsFeature(layer.fields())
        f1.setAttributes([1])
        f1.setGeometry(QgsGeometry.fromWkt(
            "POLYGON((106 10, 109 10, 109 13, 106 13, 106 10), (107 11, 108 11, 108 12, 107 12, 107 11))"
        ))

        # Feature 2: MultiPolygon
        f2 = QgsFeature(layer.fields())
        f2.setAttributes([2])
        f2.setGeometry(QgsGeometry.fromWkt(
            "MULTIPOLYGON(((100 10, 101 10, 101 11, 100 11, 100 10)), ((102 10, 103 10, 103 11, 102 11, 102 10)))"
        ))
        dp.addFeatures([f1, f2])
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "100,100,100,255"})))

        out_path = os.path.join(self.test_dir, "test_holes.kml")
        res = export_kml(layer, ExportOptions(out_path=out_path))
        self.assertEqual(res.exported_count, 2)

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        placemarks = root.findall(".//kml:Placemark", ns)
        # Placemark 1 has outerBoundaryIs and innerBoundaryIs
        p1 = placemarks[0]
        self.assertIsNotNone(p1.find(".//kml:outerBoundaryIs", ns))
        self.assertIsNotNone(p1.find(".//kml:innerBoundaryIs", ns))

        # Placemark 2 has MultiGeometry
        p2 = placemarks[1]
        self.assertIsNotNone(p2.find(".//kml:MultiGeometry", ns))
        self.assertEqual(len(p2.findall(".//kml:MultiGeometry/kml:Polygon", ns)), 2)

    def test_data_defined_override(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=color_hex:string", "ddp_layer", "memory")
        dp = layer.dataProvider()

        f1 = QgsFeature(layer.fields())
        f1.setAttributes(["#ffff00"])  # Yellow
        f1.setGeometry(QgsGeometry.fromWkt("POLYGON((106 10, 107 10, 107 11, 106 11, 106 10))"))

        f2 = QgsFeature(layer.fields())
        f2.setAttributes(["#00ffff"])  # Cyan
        f2.setGeometry(QgsGeometry.fromWkt("POLYGON((108 10, 109 10, 109 11, 108 11, 108 10))"))
        dp.addFeatures([f1, f2])

        # Base symbol is black
        sym = QgsFillSymbol.createSimple({"color": "0,0,0,255"})
        sl = sym.symbolLayer(0)
        sl.setDataDefinedProperty(QgsSymbolLayer.Property.PropertyFillColor, QgsProperty.fromExpression('"color_hex"'))
        layer.setRenderer(QgsSingleSymbolRenderer(sym))

        out_path = os.path.join(self.test_dir, "test_ddp.kml")
        res = export_kml(layer, ExportOptions(out_path=out_path))
        self.assertEqual(res.exported_count, 2)

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        styles = root.findall(".//kml:Style", ns)
        poly_colors = [s.find(".//kml:PolyStyle/kml:color", ns).text for s in styles]
        # Yellow #ffff00 -> aabbggrr = ff 00 ff ff
        self.assertIn("ff00ffff", poly_colors)
        # Cyan #00ffff -> aabbggrr = ff ff ff 00
        self.assertIn("ffffff00", poly_colors)

    def test_xml_escaping_and_vietnamese(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=name:string&field=note:string", "vn_layer", "memory")
        dp = layer.dataProvider()

        f = QgsFeature(layer.fields())
        f.setAttributes(["Trạm & Cột 4G <Hà Nội>", 'Ghi chú "Đặc biệt" & 100%'])
        f.setGeometry(QgsGeometry.fromWkt("POLYGON((106 10, 107 10, 107 11, 106 11, 106 10))"))
        dp.addFeatures([f])
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "255,0,0,255"})))

        out_path = os.path.join(self.test_dir, "test_vn.kml")
        opts = ExportOptions(out_path=out_path, name_field="name", extra_fields=["note"])
        res = export_kml(layer, opts)
        self.assertEqual(res.exported_count, 1)

        # Ensure valid XML parsing
        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        p_name = root.find(".//kml:Placemark/kml:name", ns).text
        self.assertEqual(p_name, "Trạm & Cột 4G <Hà Nội>")
        p_val = root.find(".//kml:ExtendedData/kml:Data/kml:value", ns).text
        self.assertEqual(p_val, 'Ghi chú "Đặc biệt" & 100%')

    def test_graduated_renderer(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=traffic:double", "grad_layer", "memory")
        dp = layer.dataProvider()
        feats = []
        for val in [10.0, 50.0, 90.0]:
            f = QgsFeature(layer.fields())
            f.setAttributes([val])
            f.setGeometry(QgsGeometry.fromWkt("POLYGON((106 10, 107 10, 107 11, 106 11, 106 10))"))
            feats.append(f)
        dp.addFeatures(feats)

        ranges = [
            QgsRendererRange(0.0, 30.0, QgsFillSymbol.createSimple({"color": "0,255,0,255"}), "Low"),
            QgsRendererRange(30.0, 70.0, QgsFillSymbol.createSimple({"color": "255,255,0,255"}), "Medium"),
            QgsRendererRange(70.0, 100.0, QgsFillSymbol.createSimple({"color": "255,0,0,255"}), "High"),
        ]
        renderer = QgsGraduatedSymbolRenderer("traffic", ranges)
        layer.setRenderer(renderer)

        out_path = os.path.join(self.test_dir, "test_grad.kml")
        opts = ExportOptions(out_path=out_path, group_by_category=True)
        res = export_kml(layer, opts)

        self.assertEqual(res.exported_count, 3)
        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        folders = root.findall(".//kml:Folder", ns)
        self.assertEqual(len(folders), 3)
        folder_names = [f.find("kml:name", ns).text for f in folders]
        self.assertIn("Low", folder_names)
        self.assertIn("Medium", folder_names)
        self.assertIn("High", folder_names)

    def test_rule_based_renderer(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=tech:string", "rule_layer", "memory")
        dp = layer.dataProvider()
        for t in ["2G", "4G"]:
            f = QgsFeature(layer.fields())
            f.setAttributes([t])
            f.setGeometry(QgsGeometry.fromWkt("POLYGON((106 10, 107 10, 107 11, 106 11, 106 10))"))
            dp.addFeatures([f])

        root_rule = QgsRuleBasedRenderer.Rule(None)
        rule_2g = QgsRuleBasedRenderer.Rule(
            QgsFillSymbol.createSimple({"color": "100,100,100,255"}),
            0, 0, '"tech" = \'2G\'', "Mạng 2G"
        )
        rule_4g = QgsRuleBasedRenderer.Rule(
            QgsFillSymbol.createSimple({"color": "0,0,255,255"}),
            0, 0, '"tech" = \'4G\'', "Mạng 4G"
        )
        root_rule.appendChild(rule_2g)
        root_rule.appendChild(rule_4g)
        layer.setRenderer(QgsRuleBasedRenderer(root_rule))

        out_path = os.path.join(self.test_dir, "test_rule.kml")
        opts = ExportOptions(out_path=out_path, group_by_category=True)
        res = export_kml(layer, opts)
        self.assertEqual(res.exported_count, 2)

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        folders = root.findall(".//kml:Folder", ns)
        self.assertEqual(len(folders), 2)
        folder_names = [f.find("kml:name", ns).text for f in folders]
        self.assertIn("Mạng 2G", folder_names)
        self.assertIn("Mạng 4G", folder_names)

    def test_opacity_and_width_override(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=id:int", "opt_layer", "memory")
        dp = layer.dataProvider()
        f = QgsFeature(layer.fields())
        f.setAttributes([1])
        f.setGeometry(QgsGeometry.fromWkt("POLYGON((106 10, 107 10, 107 11, 106 11, 106 10))"))
        dp.addFeatures([f])
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "255,0,0,255"})))

        out_path = os.path.join(self.test_dir, "test_override.kml")
        # 50% opacity = 0.5 (alpha 128 = 0x80), width = 3.5 px
        opts = ExportOptions(out_path=out_path, fill_alpha=0.5, stroke_width=3.5, stroke_mode="same_opaque")
        export_kml(layer, opts)

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        style = root.find(".//kml:Style", ns)

        poly_color = style.find(".//kml:PolyStyle/kml:color", ns).text
        self.assertEqual(poly_color, "800000ff")  # 50% red

        line_color = style.find(".//kml:LineStyle/kml:color", ns).text
        self.assertEqual(line_color, "ff0000ff")  # same_opaque: 100% alpha

        width_val = style.find(".//kml:LineStyle/kml:width", ns).text
        self.assertEqual(float(width_val), 3.5)

    def test_only_selected_features(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=id:int", "sel_layer", "memory")
        dp = layer.dataProvider()
        feats = []
        for i in range(5):
            f = QgsFeature(layer.fields())
            f.setAttributes([i])
            f.setGeometry(QgsGeometry.fromWkt(f"POLYGON(({106+i} 10, {107+i} 10, {107+i} 11, {106+i} 11, {106+i} 10))"))
            feats.append(f)
        dp.addFeatures(feats)
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "255,0,0,255"})))

        # Select only feature id 0 and 2
        all_fids = [f.id() for f in layer.getFeatures()]
        layer.selectByIds([all_fids[0], all_fids[2]])

        out_path = os.path.join(self.test_dir, "test_sel.kml")
        opts = ExportOptions(out_path=out_path, only_selected=True)
        res = export_kml(layer, opts)

        self.assertEqual(res.exported_count, 2)
        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        placemarks = root.findall(".//kml:Placemark", ns)
        self.assertEqual(len(placemarks), 2)

    def test_kmz_export(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=cell:string", "kmz_layer", "memory")
        dp = layer.dataProvider()
        f = QgsFeature(layer.fields())
        f.setAttributes(["Cell_KMZ"])
        f.setGeometry(QgsGeometry.fromWkt("POLYGON((106 10, 107 10, 107 11, 106 11, 106 10))"))
        dp.addFeatures([f])
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "0,128,255,255"})))

        kmz_path = os.path.join(self.test_dir, "test_compressed.kmz")
        opts = ExportOptions(out_path=kmz_path, name_field="cell")
        res = export_kml(layer, opts)

        self.assertEqual(res.exported_count, 1)
        self.assertTrue(os.path.exists(kmz_path))
        self.assertTrue(zipfile.is_zipfile(kmz_path))

        with zipfile.ZipFile(kmz_path, "r") as zf:
            file_list = zf.namelist()
            self.assertIn("doc.kml", file_list)
            kml_content = zf.read("doc.kml").decode("utf-8")
            root = ET.fromstring(kml_content)
            ns = {"kml": "http://www.opengis.net/kml/2.2"}
            p_name = root.find(".//kml:Placemark/kml:name", ns).text
            self.assertEqual(p_name, "Cell_KMZ")

    def test_geometry_scaling(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=site:string", "scale_layer", "memory")
        dp = layer.dataProvider()
        f = QgsFeature(layer.fields())
        f.setAttributes(["SiteA"])
        # Cell sector starting at tower (106.0, 10.0)
        f.setGeometry(QgsGeometry.fromWkt("POLYGON((106.0 10.0, 106.02 10.05, 106.04 10.04, 106.0 10.0))"))
        dp.addFeatures([f])
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "255,0,0,255"})))

        out_path = os.path.join(self.test_dir, "test_scale_150.kml")
        # Scale 150% (+50%) anchored at first_vertex (site origin)
        opts = ExportOptions(out_path=out_path, scale_factor=1.5, scale_anchor="first_vertex")
        res = export_kml(layer, opts)
        self.assertEqual(res.exported_count, 1)

        tree = ET.parse(out_path)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        coord_text = root.find(".//kml:coordinates", ns).text.strip()
        pts = [c.split(",") for c in coord_text.split()]

        # First vertex (tower) must remain unchanged at (106.0, 10.0)
        p0_x = float(pts[0][0])
        p0_y = float(pts[0][1])
        self.assertAlmostEqual(p0_x, 106.0, places=5)
        self.assertAlmostEqual(p0_y, 10.0, places=5)

        # Petal outer point (orig 106.02, 10.05 -> scaled with anchor 106.0, 10.0: 106.0 + 1.5*(0.02) = 106.03)
        p1_x = float(pts[1][0])
        p1_y = float(pts[1][1])
        self.assertAlmostEqual(p1_x, 106.03, places=5)
        self.assertAlmostEqual(p1_y, 10.075, places=5)

    def test_updater_logic(self):
        from qgis2ge.updater import (
            get_current_version,
            install_update_from_zip,
            parse_version,
        )

        # Version parsing tests
        self.assertTrue(parse_version("v1.2.0") > parse_version("1.1.0"))
        self.assertTrue(parse_version("1.10.0") > parse_version("1.9.9"))
        self.assertFalse(parse_version("1.1.0") > parse_version("1.1.0"))
        self.assertFalse(parse_version("1.0.9") > parse_version("1.1.0"))

        current = get_current_version()
        self.assertTrue(len(current) > 0)

        # Test local update extraction
        mock_target = os.path.join(self.test_dir, "mock_plugin")
        os.makedirs(mock_target, exist_ok=True)
        with open(os.path.join(mock_target, "metadata.txt"), "w", encoding="utf-8") as f:
            f.write("[general]\nversion=1.0.0\n")

        # Create mock update zip
        mock_zip_path = os.path.join(self.test_dir, "mock_update.zip")
        with zipfile.ZipFile(mock_zip_path, "w") as zf:
            zf.writestr("metadata.txt", "[general]\nversion=2.0.0\n")
            zf.writestr("test_file.txt", "Updated Content")

        # Mock download URL using file:// URI
        file_url = f"file:///{os.path.abspath(mock_zip_path).replace(os.sep, '/')}"
        success, msg = install_update_from_zip(file_url, target_plugin_dir=mock_target)

        self.assertTrue(success)
        # Verify metadata was updated
        with open(os.path.join(mock_target, "metadata.txt"), "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("version=2.0.0", content)
        self.assertTrue(os.path.exists(os.path.join(mock_target, "test_file.txt")))

    def test_cancellation(self):
        layer = QgsVectorLayer("Polygon?crs=epsg:4326&field=id:int", "cancel_layer", "memory")
        dp = layer.dataProvider()
        feats = []
        for i in range(10):
            f = QgsFeature(layer.fields())
            f.setAttributes([i])
            f.setGeometry(QgsGeometry.fromWkt(f"POLYGON(({106+i} 10, {107+i} 10, {107+i} 11, {106+i} 11, {106+i} 10))"))
            feats.append(f)
        dp.addFeatures(feats)
        layer.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({"color": "255,0,0,255"})))

        out_path = os.path.join(self.test_dir, "test_cancel.kml")
        # Cancel after 2 iterations
        feedback = DummyFeedback(cancel_after=2)
        res = export_kml(layer, ExportOptions(out_path=out_path), feedback=feedback)

        self.assertTrue(res.canceled)
        # Check that file was not created or deleted
        self.assertFalse(os.path.exists(out_path))


if __name__ == "__main__":
    unittest.main()
