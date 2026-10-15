"""Core exporter logic for KML/KMZ Color Export QGIS plugin.

Independent of GUI, handles feature styling, geometry scaling and transformation,
style deduplication, streaming KML creation, and direct KMZ compression.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import xml.sax.saxutils as saxutils
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsGraduatedSymbolRenderer,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsRuleBasedRenderer,
    QgsSymbol,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor


@dataclass
class ExportOptions:
    """Options configuring KML/KMZ color export."""

    out_path: str
    name_field: Optional[str] = None
    extra_fields: List[str] = field(default_factory=list)
    only_selected: bool = False
    stroke_mode: str = "same"  # "same" | "same_opaque" | "original" | "none"
    stroke_width: Optional[float] = None  # None = from symbol, else in pixels
    group_by_category: bool = False
    fill_alpha: Optional[float] = None  # None = from symbol, else 0.0..1.0
    scale_factor: float = 1.0  # 1.0 = 100%, 1.5 = +50%
    scale_anchor: str = "first_vertex"  # "first_vertex" (cell site/tower) | "centroid"


@dataclass
class ExportResult:
    """Result summary of KML/KMZ export execution."""

    exported_count: int
    skipped_count: int
    output_path: str
    warnings: List[str] = field(default_factory=list)
    canceled: bool = False


def xml_escape(value: Any) -> str:
    """Escape XML special characters in string representation."""
    if value is None:
        return ""
    text = str(value)
    return saxutils.escape(text, entities={'"': "&quot;", "'": "&apos;"})


def qcolor_to_kml_hex(r: int, g: int, b: int, a: int) -> str:
    """Convert RGBA components to KML 8-hex character format aabbggrr."""
    clamped_a = max(0, min(255, int(a)))
    clamped_r = max(0, min(255, int(r)))
    clamped_g = max(0, min(255, int(g)))
    clamped_b = max(0, min(255, int(b)))
    return f"{clamped_a:02x}{clamped_b:02x}{clamped_g:02x}{clamped_r:02x}".lower()


def scale_geometry(
    geom: QgsGeometry, scale_factor: float, scale_anchor: str = "first_vertex"
) -> QgsGeometry:
    """Scale geometry around anchor point.

    For telecom cell sectors / pies, 'first_vertex' keeps the antenna tower
    anchored at the origin while expanding the petal outward.
    'centroid' expands or shrinks around the center of mass.
    """
    if abs(scale_factor - 1.0) < 1e-4 or geom.isNull() or geom.isEmpty():
        return geom

    if geom.isMultipart():
        parts = geom.asMultiPolygon()
        if not parts:
            return geom
        new_parts = []
        for poly in parts:
            if not poly or not poly[0]:
                continue
            if scale_anchor == "first_vertex":
                anchor = poly[0][0]  # Site origin vertex
            else:
                c = geom.centroid().asPoint()
                anchor = QgsPointXY(c.x(), c.y())

            new_poly = []
            for ring in poly:
                new_ring = []
                for pt in ring:
                    nx = anchor.x() + scale_factor * (pt.x() - anchor.x())
                    ny = anchor.y() + scale_factor * (pt.y() - anchor.y())
                    new_ring.append(QgsPointXY(nx, ny))
                new_poly.append(new_ring)
            new_parts.append(new_poly)
        scaled = QgsGeometry.fromMultiPolygonXY(new_parts)
        return scaled if not scaled.isNull() and not scaled.isEmpty() else geom
    else:
        poly = geom.asPolygon()
        if not poly or not poly[0]:
            return geom
        if scale_anchor == "first_vertex":
            anchor = poly[0][0]  # Site origin vertex
        else:
            c = geom.centroid().asPoint()
            anchor = QgsPointXY(c.x(), c.y())

        new_poly = []
        for ring in poly:
            new_ring = []
            for pt in ring:
                nx = anchor.x() + scale_factor * (pt.x() - anchor.x())
                ny = anchor.y() + scale_factor * (pt.y() - anchor.y())
                new_ring.append(QgsPointXY(nx, ny))
            new_poly.append(new_ring)
        scaled = QgsGeometry.fromPolygonXY(new_poly)
        return scaled if not scaled.isNull() and not scaled.isEmpty() else geom


def extract_polygons(geom: QgsGeometry) -> List[Any]:
    """Extract list of polygons from QgsGeometry (each polygon is a list of rings).

    Each ring is a list of QgsPointXY / QgsPoint.
    Ring 0 is outer ring; rings 1..N are inner rings (holes).
    """
    if geom.isNull() or geom.isEmpty():
        return []

    if hasattr(geom, "convertToStraightSegment"):
        geom.convertToStraightSegment()

    if geom.isMultipart():
        return geom.asMultiPolygon()
    else:
        poly = geom.asPolygon()
        return [poly] if poly else []


def get_feature_category(
    renderer: Any, feat: QgsFeature, context: QgsRenderContext
) -> str:
    """Determine category label for grouping placemarks into KML Folders."""
    if isinstance(renderer, QgsCategorizedSymbolRenderer):
        attr_name = renderer.classAttribute()
        val = feat[attr_name] if attr_name in feat.fields().names() else None
        if val is None or val == "" or (isinstance(val, QVariant) and val.isNull()):
            return "Other"
        for cat in renderer.categories():
            if cat.value() == val:
                return cat.label() or str(val)
        return str(val)

    elif isinstance(renderer, QgsGraduatedSymbolRenderer):
        attr_name = renderer.classAttribute()
        val = feat[attr_name] if attr_name in feat.fields().names() else None
        if val is not None and not (isinstance(val, QVariant) and val.isNull()):
            try:
                num = float(val)
                for rng in renderer.ranges():
                    if rng.lowerValue() <= num <= rng.upperValue():
                        return rng.label()
            except (ValueError, TypeError):
                pass
        return "Other"

    elif isinstance(renderer, QgsRuleBasedRenderer):
        root = renderer.rootRule()

        def find_rule(rule: Any) -> Optional[str]:
            for child in rule.children():
                if child.active() and child.isFilterOK(feat, context):
                    sub = find_rule(child)
                    return sub if sub else child.label()
            return None

        lbl = find_rule(root)
        return lbl if lbl else "Default"

    return "All"


def evaluate_feature_style(
    feat: QgsFeature,
    sym: QgsSymbol,
    context: QgsRenderContext,
    options: ExportOptions,
    layer_opacity: float,
    warnings: List[str],
) -> Tuple[str, str, float, int]:
    """Evaluate colors, stroke width, and outline flag for a feature.

    Returns:
        (fill_kml, stroke_kml, stroke_width, outline_flag)
    """
    exp_ctx = context.expressionContext()

    target_sl: Optional[QgsSymbolLayer] = None
    symbol_layers = sym.symbolLayers() if hasattr(sym, "symbolLayers") else []

    if len(symbol_layers) > 1 and "simplified_layers" not in warnings:
        warnings.append("Multi-layer symbol simplified: first fill layer used.")

    for sl in symbol_layers:
        if hasattr(sl, "fillColor"):
            target_sl = sl
            break

    # Determine base fill color
    if target_sl is not None:
        fill_color = target_sl.fillColor()
        ddp = target_sl.dataDefinedProperties()
        if ddp.hasProperty(QgsSymbolLayer.Property.PropertyFillColor):
            val = ddp.value(QgsSymbolLayer.Property.PropertyFillColor, exp_ctx, fill_color)
            if isinstance(val, QColor) and val.isValid():
                fill_color = val
            elif isinstance(val, str) and val:
                c = QColor(val)
                if c.isValid():
                    fill_color = c
    else:
        fill_color = sym.color()

    # Determine base stroke color
    stroke_color = QColor(0, 0, 0, 255)
    if target_sl is not None and hasattr(target_sl, "strokeColor"):
        stroke_color = target_sl.strokeColor()
        ddp = target_sl.dataDefinedProperties()
        if ddp.hasProperty(QgsSymbolLayer.Property.PropertyStrokeColor):
            val = ddp.value(QgsSymbolLayer.Property.PropertyStrokeColor, exp_ctx, stroke_color)
            if isinstance(val, QColor) and val.isValid():
                stroke_color = val
            elif isinstance(val, str) and val:
                c = QColor(val)
                if c.isValid():
                    stroke_color = c

    # Determine base stroke width (QGIS mm to px)
    stroke_width_val = 0.26
    if target_sl is not None and hasattr(target_sl, "strokeWidth"):
        stroke_width_val = target_sl.strokeWidth()
        ddp = target_sl.dataDefinedProperties()
        if ddp.hasProperty(QgsSymbolLayer.Property.PropertyStrokeWidth):
            val = ddp.value(QgsSymbolLayer.Property.PropertyStrokeWidth, exp_ctx, stroke_width_val)
            if isinstance(val, (int, float)):
                stroke_width_val = float(val)

    # Calculate final fill alpha
    sym_opacity = getattr(sym, "opacity", lambda: 1.0)() * layer_opacity
    if options.fill_alpha is not None:
        final_fill_alpha = int(round(max(0.0, min(1.0, options.fill_alpha)) * 255))
    else:
        final_fill_alpha = int(round(fill_color.alpha() * sym_opacity))

    # Calculate stroke color and outline based on stroke_mode
    outline_flag = 1
    if options.stroke_mode == "none":
        outline_flag = 0
        final_stroke_color = stroke_color
    elif options.stroke_mode == "same":
        final_stroke_color = QColor(
            fill_color.red(), fill_color.green(), fill_color.blue(), final_fill_alpha
        )
    elif options.stroke_mode == "same_opaque":
        final_stroke_color = QColor(
            fill_color.red(), fill_color.green(), fill_color.blue(), 255
        )
    elif options.stroke_mode == "original":
        orig_alpha = int(round(stroke_color.alpha() * sym_opacity))
        final_stroke_color = QColor(
            stroke_color.red(), stroke_color.green(), stroke_color.blue(), orig_alpha
        )
    else:
        final_stroke_color = QColor(
            fill_color.red(), fill_color.green(), fill_color.blue(), final_fill_alpha
        )

    # Calculate stroke width
    if options.stroke_width is not None:
        final_stroke_width = max(0.5, float(options.stroke_width))
    else:
        final_stroke_width = max(0.5, round(stroke_width_val * 3.78, 2))

    fill_kml = qcolor_to_kml_hex(
        fill_color.red(), fill_color.green(), fill_color.blue(), final_fill_alpha
    )
    stroke_kml = qcolor_to_kml_hex(
        final_stroke_color.red(),
        final_stroke_color.green(),
        final_stroke_color.blue(),
        final_stroke_color.alpha(),
    )

    return (fill_kml, stroke_kml, final_stroke_width, outline_flag)


def export_kml(
    layer: QgsVectorLayer,
    options: ExportOptions,
    feedback: Optional[Any] = None,
) -> ExportResult:
    """Export layer polygons to a styled KML or KMZ file.

    Args:
        layer: Target QgsVectorLayer.
        options: ExportOptions configuration.
        feedback: Optional QgsFeedback or QgsTask instance with isCanceled() and setProgress().

    Returns:
        ExportResult containing statistics and generated file path.
    """
    if layer is None or not layer.isValid():
        raise ValueError("Invalid or empty vector layer.")

    source_crs = layer.crs()
    if not source_crs.isValid():
        raise ValueError("Layer Coordinate Reference System (CRS) is undefined or invalid.")

    dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())

    # Prepare features iterator
    if options.only_selected:
        features = list(layer.selectedFeatures())
        total_features = len(features)
    else:
        features = layer.getFeatures()
        total_features = layer.featureCount()
        if total_features < 0:
            total_features = 0

    # Ensure output directory exists
    out_dir = os.path.dirname(options.out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    is_kmz = options.out_path.lower().endswith(".kmz")

    # Setup render context
    context = QgsRenderContext()
    exp_context = layer.createExpressionContext()
    context.setExpressionContext(exp_context)

    renderer = layer.renderer().clone()
    renderer.startRender(context, layer.fields())

    layer_opacity = layer.opacity()
    warnings: List[str] = []

    style_cache: Dict[Tuple[str, str, float, int], str] = {}

    temp_dir = tempfile.mkdtemp(prefix="kml_export_")
    folder_files: Dict[str, Any] = {}
    folder_order: List[str] = []
    single_temp_file: Optional[Any] = None

    exported_count = 0
    skipped_count = 0
    canceled = False

    try:
        if not options.group_by_category:
            single_temp_file = open(
                os.path.join(temp_dir, "placemarks.tmp"), "w", encoding="utf-8"
            )

        processed = 0

        for feat in features:
            if feedback and feedback.isCanceled():
                canceled = True
                break

            processed += 1
            if total_features > 0 and feedback:
                feedback.setProgress(int((processed / total_features) * 85))

            geom = feat.geometry()
            if geom.isNull() or geom.isEmpty():
                skipped_count += 1
                continue

            if not geom.isGeosValid():
                geom = geom.makeValid()
                if geom.isNull() or geom.isEmpty() or not geom.isGeosValid():
                    skipped_count += 1
                    continue

            # Transform to EPSG:4326
            try:
                geom_4326 = QgsGeometry(geom)
                geom_4326.transform(transform)
                if geom_4326.isNull() or geom_4326.isEmpty():
                    skipped_count += 1
                    continue
            except Exception:
                skipped_count += 1
                continue

            # Scale geometry if requested (e.g. +50% cell sectors)
            if abs(options.scale_factor - 1.0) >= 1e-4:
                geom_4326 = scale_geometry(geom_4326, options.scale_factor, options.scale_anchor)
                if geom_4326.isNull() or geom_4326.isEmpty():
                    skipped_count += 1
                    continue

            polygons = extract_polygons(geom_4326)
            if not polygons:
                skipped_count += 1
                continue

            # Evaluate symbol
            context.expressionContext().setFeature(feat)
            sym = None
            if hasattr(renderer, "symbolsForFeature"):
                syms = renderer.symbolsForFeature(feat, context)
                if syms:
                    sym = syms[0]
            if sym is None and hasattr(renderer, "symbolForFeature"):
                sym = renderer.symbolForFeature(feat, context)

            if sym is None:
                continue

            style_key = evaluate_feature_style(
                feat, sym, context, options, layer_opacity, warnings
            )
            if style_key not in style_cache:
                style_id = f"s{len(style_cache)}"
                style_cache[style_key] = style_id
            else:
                style_id = style_cache[style_key]

            # Build Placemark XML
            placemark_xml_parts: List[str] = ["    <Placemark>\n"]

            # Placemark name
            if options.name_field:
                if options.name_field in ("__fid__", "[Feature ID]"):
                    name_val = str(feat.id())
                elif options.name_field in feat.fields().names():
                    val = feat[options.name_field]
                    name_val = "" if val is None or (isinstance(val, QVariant) and val.isNull()) else str(val)
                else:
                    name_val = ""
                if name_val:
                    placemark_xml_parts.append(f"      <name>{xml_escape(name_val)}</name>\n")

            # Style reference
            placemark_xml_parts.append(f"      <styleUrl>#{style_id}</styleUrl>\n")

            # ExtendedData
            if options.extra_fields:
                ext_parts: List[str] = ["      <ExtendedData>\n"]
                for f_name in options.extra_fields:
                    if f_name in feat.fields().names():
                        raw_v = feat[f_name]
                        str_v = (
                            ""
                            if raw_v is None or (isinstance(raw_v, QVariant) and raw_v.isNull())
                            else str(raw_v)
                        )
                        ext_parts.append(
                            f'        <Data name="{xml_escape(f_name)}">\n'
                            f"          <value>{xml_escape(str_v)}</value>\n"
                            f"        </Data>\n"
                        )
                ext_parts.append("      </ExtendedData>\n")
                placemark_xml_parts.extend(ext_parts)

            # Geometry XML
            if len(polygons) == 1:
                placemark_xml_parts.append("      <Polygon>\n")
                outer_ring = polygons[0][0]
                coord_str = " ".join(f"{pt.x():.7f},{pt.y():.7f},0" for pt in outer_ring)
                placemark_xml_parts.append(
                    "        <outerBoundaryIs>\n"
                    "          <LinearRing>\n"
                    f"            <coordinates>{coord_str}</coordinates>\n"
                    "          </LinearRing>\n"
                    "        </outerBoundaryIs>\n"
                )
                for inner_ring in polygons[0][1:]:
                    coord_str = " ".join(f"{pt.x():.7f},{pt.y():.7f},0" for pt in inner_ring)
                    placemark_xml_parts.append(
                        "        <innerBoundaryIs>\n"
                        "          <LinearRing>\n"
                        f"            <coordinates>{coord_str}</coordinates>\n"
                        "          </LinearRing>\n"
                        "        </innerBoundaryIs>\n"
                    )
                placemark_xml_parts.append("      </Polygon>\n")
            else:
                placemark_xml_parts.append("      <MultiGeometry>\n")
                for poly in polygons:
                    placemark_xml_parts.append("        <Polygon>\n")
                    outer_ring = poly[0]
                    coord_str = " ".join(f"{pt.x():.7f},{pt.y():.7f},0" for pt in outer_ring)
                    placemark_xml_parts.append(
                        "          <outerBoundaryIs>\n"
                        "            <LinearRing>\n"
                        f"              <coordinates>{coord_str}</coordinates>\n"
                        "            </LinearRing>\n"
                        "          </outerBoundaryIs>\n"
                    )
                    for inner_ring in poly[1:]:
                        coord_str = " ".join(f"{pt.x():.7f},{pt.y():.7f},0" for pt in inner_ring)
                        placemark_xml_parts.append(
                            "          <innerBoundaryIs>\n"
                            "            <LinearRing>\n"
                            f"              <coordinates>{coord_str}</coordinates>\n"
                            "            </LinearRing>\n"
                            "          </innerBoundaryIs>\n"
                        )
                    placemark_xml_parts.append("        </Polygon>\n")
                placemark_xml_parts.append("      </MultiGeometry>\n")

            placemark_xml_parts.append("    </Placemark>\n")
            full_placemark_xml = "".join(placemark_xml_parts)

            # Write to stream
            if options.group_by_category:
                cat = get_feature_category(renderer, feat, context)
                if cat not in folder_files:
                    f_tmp = open(
                        os.path.join(temp_dir, f"f_{len(folder_files)}.tmp"),
                        "w",
                        encoding="utf-8",
                    )
                    folder_files[cat] = f_tmp
                    folder_order.append(cat)
                folder_files[cat].write(full_placemark_xml)
            else:
                if single_temp_file is not None:
                    single_temp_file.write(full_placemark_xml)

            exported_count += 1

        # Close all temp files before assembly
        if single_temp_file is not None:
            single_temp_file.close()
            single_temp_file = None

        for f_tmp in folder_files.values():
            f_tmp.close()

        if canceled:
            if os.path.exists(options.out_path):
                try:
                    os.remove(options.out_path)
                except OSError:
                    pass
            return ExportResult(
                exported_count=0,
                skipped_count=skipped_count,
                output_path=options.out_path,
                warnings=warnings,
                canceled=True,
            )

        # Final Assembly
        if feedback:
            feedback.setProgress(90)

        # For KMZ, write to a temp doc.kml first
        kml_target_path = (
            os.path.join(temp_dir, "doc.kml") if is_kmz else options.out_path
        )

        with open(kml_target_path, "w", encoding="utf-8") as out_f:
            out_f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            out_f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
            out_f.write("  <Document>\n")
            out_f.write(f"    <name>{xml_escape(layer.name())}</name>\n")

            for (fill_kml, stroke_kml, width, outline), style_id in style_cache.items():
                out_f.write(f'    <Style id="{style_id}">\n')
                out_f.write("      <LineStyle>\n")
                out_f.write(f"        <color>{stroke_kml}</color>\n")
                out_f.write(f"        <width>{width:.2f}</width>\n")
                out_f.write("      </LineStyle>\n")
                out_f.write("      <PolyStyle>\n")
                out_f.write(f"        <color>{fill_kml}</color>\n")
                out_f.write("        <fill>1</fill>\n")
                out_f.write(f"        <outline>{outline}</outline>\n")
                out_f.write("      </PolyStyle>\n")
                out_f.write("    </Style>\n")

            if options.group_by_category:
                for idx, cat in enumerate(folder_order):
                    out_f.write("    <Folder>\n")
                    out_f.write(f"      <name>{xml_escape(cat)}</name>\n")
                    tmp_p = os.path.join(temp_dir, f"f_{idx}.tmp")
                    if os.path.exists(tmp_p):
                        with open(tmp_p, "r", encoding="utf-8") as tf:
                            shutil.copyfileobj(tf, out_f)
                    out_f.write("    </Folder>\n")
            else:
                tmp_p = os.path.join(temp_dir, "placemarks.tmp")
                if os.path.exists(tmp_p):
                    with open(tmp_p, "r", encoding="utf-8") as tf:
                        shutil.copyfileobj(tf, out_f)

            out_f.write("  </Document>\n")
            out_f.write("</kml>\n")

        # If KMZ, compress into zip archive
        if is_kmz:
            if feedback:
                feedback.setProgress(95)
            with zipfile.ZipFile(
                options.out_path, "w", compression=zipfile.ZIP_DEFLATED
            ) as zip_out:
                zip_out.write(kml_target_path, arcname="doc.kml")

        if feedback:
            feedback.setProgress(100)

    finally:
        try:
            renderer.stopRender(context)
        except Exception:
            pass

        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    return ExportResult(
        exported_count=exported_count,
        skipped_count=skipped_count,
        output_path=options.out_path,
        warnings=warnings,
        canceled=canceled,
    )
