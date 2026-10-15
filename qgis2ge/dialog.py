"""Modern unified UI dialog for qgis2ge QGIS plugin.

Designed with QGIS-native visual hierarchy, responsive grid alignment,
clean rounded card containers, color swatch preview, geometry scaling,
direct KMZ compression, and in-app updates.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsGraduatedSymbolRenderer,
    QgsMapLayer,
    QgsProject,
    QgsRuleBasedRenderer,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QFileInfo, QTimer, Qt, QUrl
from qgis.PyQt.QtGui import (
    QBrush,
    QColor,
    QDesktopServices,
    QIcon,
    QPainter,
    QPen,
    QPixmap,
)
from qgis.PyQt.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from qgis2ge.exporter import ExportOptions, ExportResult
from qgis2ge.task import KmlExportTask
from qgis2ge.updater import (
    CheckUpdateTask,
    InstallUpdateTask,
    UpdateInfo,
    get_current_version,
)


class Qgis2GeDialog(QDialog):
    """Main export dialog for qgis2ge (QGIS to Google Earth)."""

    SETTINGS_PREFIX = "qgis2ge/"
    LABEL_COL_WIDTH = 135

    def __init__(self, iface: Any, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.iface = iface
        self.setObjectName("Qgis2GeDialog")
        self.setWindowTitle(self.tr("qgis2ge - QGIS to Google Earth"))

        self.resize(580, 640)
        self.setMinimumSize(520, 540)

        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, "icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.current_task: Optional[KmlExportTask] = None
        self.settings = QgsSettings()
        self.current_version = get_current_version()
        self.latest_update_info: Optional[UpdateInfo] = None
        self.check_update_task: Optional[CheckUpdateTask] = None
        self.install_update_task: Optional[InstallUpdateTask] = None

        self._setup_ui(icon_path)
        self._load_stylesheet(plugin_dir)
        self._populate_layers()
        self._load_settings()
        self._update_ui_state()

    def _load_stylesheet(self, plugin_dir: str) -> None:
        """Load and apply styles.qss stylesheet."""
        qss_path = os.path.join(plugin_dir, "styles.qss")
        if os.path.exists(qss_path):
            try:
                with open(qss_path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as exc:
                _ = exc

    def _setup_ui(self, icon_path: str) -> None:
        """Construct the cohesive, grid-aligned interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 14)
        main_layout.setSpacing(10)

        # Scroll Area for fluid responsiveness
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(10)

        # 1. Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(12)

        icon_label = QLabel()
        if os.path.exists(icon_path):
            icon_label.setPixmap(QIcon(icon_path).pixmap(44, 44))
        header_layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(3)

        lbl_title = QLabel(self.tr("qgis2ge"))
        lbl_title.setObjectName("headerTitle")

        lbl_sub = QLabel(
            self.tr("Export polygon layers to Google Earth (KML/KMZ) preserving styles, colors, opacity, and scale")
        )
        lbl_sub.setObjectName("headerSubtitle")
        lbl_sub.setWordWrap(True)

        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_sub)
        header_layout.addLayout(title_vbox, 1)

        # Version Badge & Check Updates Pill Button
        vbox_actions = QVBoxLayout()
        vbox_actions.setSpacing(4)
        vbox_actions.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        self.lbl_version_badge = QLabel(f"v{self.current_version}")
        self.lbl_version_badge.setObjectName("badgeVersion")
        h_buttons = QHBoxLayout()
        h_buttons.setSpacing(6)

        self.btn_check_update = QPushButton(self.tr("Check for Updates"))
        self.btn_check_update.setObjectName("btnCheckUpdate")
        self.btn_check_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_update.clicked.connect(self._on_check_update)

        self.btn_reload = QPushButton(self.tr("⟳ Reload"))
        self.btn_reload.setObjectName("btnCleanReload")
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload.setToolTip(self.tr("Clean reload all plugin files from disk without restarting QGIS"))
        self.btn_reload.clicked.connect(self._on_clean_reload)

        h_buttons.addWidget(self.btn_check_update)
        h_buttons.addWidget(self.btn_reload)

        vbox_actions.addWidget(self.lbl_version_badge, 0, Qt.AlignmentFlag.AlignRight)
        vbox_actions.addLayout(h_buttons)
        header_layout.addLayout(vbox_actions)

        self.content_layout.addWidget(header_frame)

        # Card 1: Data Source
        card_data, layout_data = self._create_card(self.tr("1. Data Source"))
        grid_data = QGridLayout()
        grid_data.setContentsMargins(0, 4, 0, 0)
        grid_data.setHorizontalSpacing(12)
        grid_data.setVerticalSpacing(8)
        grid_data.setColumnMinimumWidth(0, self.LABEL_COL_WIDTH)
        grid_data.setColumnStretch(1, 1)

        lbl_layer = QLabel(self.tr("Polygon layer:"))
        lbl_layer.setProperty("class", "FormLabel")
        self.cbo_layer = QComboBox()
        self.cbo_layer.currentIndexChanged.connect(self._on_layer_changed)
        grid_data.addWidget(lbl_layer, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_data.addWidget(self.cbo_layer, 0, 1)

        lbl_sel = QLabel(self.tr("Feature selection:"))
        lbl_sel.setProperty("class", "FormLabel")
        self.chk_selected = QCheckBox(self.tr("Export selected features only"))
        self.chk_selected.setEnabled(False)
        self.chk_selected.stateChanged.connect(self._update_ui_state)
        grid_data.addWidget(lbl_sel, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_data.addWidget(self.chk_selected, 1, 1)

        layout_data.addLayout(grid_data)
        self.content_layout.addWidget(card_data)

        # Card 2: Styling & Sizing (Appearance)
        card_style, layout_style = self._create_card(self.tr("2. Styling & Sizing"))
        grid_style = QGridLayout()
        grid_style.setContentsMargins(0, 4, 0, 0)
        grid_style.setHorizontalSpacing(12)
        grid_style.setVerticalSpacing(10)
        grid_style.setColumnMinimumWidth(0, self.LABEL_COL_WIDTH)
        grid_style.setColumnStretch(1, 1)

        # Placemark Name
        lbl_name = QLabel(self.tr("Placemark name:"))
        lbl_name.setProperty("class", "FormLabel")
        self.cbo_name_field = QComboBox()
        grid_style.addWidget(lbl_name, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_style.addWidget(self.cbo_name_field, 0, 1)

        # Stroke Mode (2x2 radio grid)
        lbl_stroke = QLabel(self.tr("Stroke mode:"))
        lbl_stroke.setProperty("class", "FormLabel")

        self.btn_group_stroke = QButtonGroup(self)
        self.rdo_stroke_same = QRadioButton(self.tr("Same as fill (default)"))
        self.rdo_stroke_opaque = QRadioButton(self.tr("Same as fill (100% opaque)"))
        self.rdo_stroke_orig = QRadioButton(self.tr("Keep original symbol border"))
        self.rdo_stroke_none = QRadioButton(self.tr("No border"))

        self.btn_group_stroke.addButton(self.rdo_stroke_same, 0)
        self.btn_group_stroke.addButton(self.rdo_stroke_opaque, 1)
        self.btn_group_stroke.addButton(self.rdo_stroke_orig, 2)
        self.btn_group_stroke.addButton(self.rdo_stroke_none, 3)
        self.rdo_stroke_same.setChecked(True)

        self.rdo_stroke_same.toggled.connect(self._on_stroke_mode_changed)
        self.rdo_stroke_opaque.toggled.connect(self._on_stroke_mode_changed)
        self.rdo_stroke_orig.toggled.connect(self._on_stroke_mode_changed)
        self.rdo_stroke_none.toggled.connect(self._on_stroke_mode_changed)

        rdo_container = QWidget()
        rdo_grid = QGridLayout(rdo_container)
        rdo_grid.setContentsMargins(0, 0, 0, 0)
        rdo_grid.setHorizontalSpacing(16)
        rdo_grid.setVerticalSpacing(6)
        rdo_grid.addWidget(self.rdo_stroke_same, 0, 0)
        rdo_grid.addWidget(self.rdo_stroke_opaque, 0, 1)
        rdo_grid.addWidget(self.rdo_stroke_orig, 1, 0)
        rdo_grid.addWidget(self.rdo_stroke_none, 1, 1)

        grid_style.addWidget(lbl_stroke, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        grid_style.addWidget(rdo_container, 1, 1)

        # Stroke Width
        lbl_width = QLabel(self.tr("Stroke width:"))
        lbl_width.setProperty("class", "FormLabel")

        h_width = QHBoxLayout()
        h_width.setContentsMargins(0, 0, 0, 0)
        h_width.setSpacing(12)
        self.chk_stroke_symbol = QCheckBox(self.tr("From symbol"))
        self.chk_stroke_symbol.setChecked(False)

        self.spn_stroke_width = QDoubleSpinBox()
        self.spn_stroke_width.setRange(0.5, 20.0)
        self.spn_stroke_width.setSingleStep(0.5)
        self.spn_stroke_width.setValue(1.0)
        self.spn_stroke_width.setSuffix(" px")
        self.spn_stroke_width.setFixedWidth(100)
        self.chk_stroke_symbol.toggled.connect(lambda checked: self.spn_stroke_width.setEnabled(not checked))

        h_width.addWidget(self.chk_stroke_symbol)
        h_width.addWidget(self.spn_stroke_width)
        h_width.addStretch(1)

        grid_style.addWidget(lbl_width, 2, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_style.addLayout(h_width, 2, 1)

        # Fill Opacity
        lbl_alpha = QLabel(self.tr("Fill opacity:"))
        lbl_alpha.setProperty("class", "FormLabel")

        h_alpha = QHBoxLayout()
        h_alpha.setContentsMargins(0, 0, 0, 0)
        h_alpha.setSpacing(12)
        self.chk_alpha_symbol = QCheckBox(self.tr("From symbol"))
        self.chk_alpha_symbol.setChecked(True)

        self.sld_alpha = QSlider(Qt.Orientation.Horizontal)
        self.sld_alpha.setRange(0, 100)
        self.sld_alpha.setValue(80)
        self.sld_alpha.setEnabled(False)

        self.lbl_alpha_val = QLabel("80%")
        self.lbl_alpha_val.setFixedWidth(40)
        self.lbl_alpha_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_alpha_val.setEnabled(False)

        self.sld_alpha.valueChanged.connect(lambda v: self.lbl_alpha_val.setText(f"{v}%"))
        self.chk_alpha_symbol.toggled.connect(self._on_alpha_symbol_toggled)

        h_alpha.addWidget(self.chk_alpha_symbol)
        h_alpha.addWidget(self.sld_alpha, 1)
        h_alpha.addWidget(self.lbl_alpha_val)

        grid_style.addWidget(lbl_alpha, 3, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_style.addLayout(h_alpha, 3, 1)

        # Size Scaling
        lbl_scale = QLabel(self.tr("Size scaling:"))
        lbl_scale.setProperty("class", "FormLabel")

        h_scale = QHBoxLayout()
        h_scale.setContentsMargins(0, 0, 0, 0)
        h_scale.setSpacing(10)

        self.spn_scale = QSpinBox()
        self.spn_scale.setRange(20, 500)
        self.spn_scale.setSingleStep(10)
        self.spn_scale.setValue(100)
        self.spn_scale.setSuffix("%")
        self.spn_scale.setFixedWidth(85)
        self.spn_scale.setToolTip(self.tr("Scale polygon size. 100% = original size, 150% = +50% larger."))

        self.cbo_scale_anchor = QComboBox()
        self.cbo_scale_anchor.addItem(
            self.tr("Site origin / First vertex (cell sectors/pies)"), "first_vertex"
        )
        self.cbo_scale_anchor.addItem(
            self.tr("Centroid (geometry center)"), "centroid"
        )
        self.cbo_scale_anchor.setToolTip(
            self.tr("For cell sectors, 'Site origin' keeps the antenna tower fixed while expanding the sector petal outward.")
        )

        h_scale.addWidget(self.spn_scale)
        h_scale.addWidget(self.cbo_scale_anchor, 1)

        grid_style.addWidget(lbl_scale, 4, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_style.addLayout(h_scale, 4, 1)

        # Color Swatches Preview
        lbl_swatches = QLabel(self.tr("Color preview:"))
        lbl_swatches.setProperty("class", "FormLabel")

        self.swatches_scroll = QScrollArea()
        self.swatches_scroll.setObjectName("swatchesScrollArea")
        self.swatches_scroll.setFixedHeight(26)
        self.swatches_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.swatches_scroll.setWidgetResizable(True)
        self.swatches_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.swatches_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.swatches_container = QWidget()
        self.swatches_layout = QHBoxLayout(self.swatches_container)
        self.swatches_layout.setContentsMargins(0, 2, 0, 2)
        self.swatches_layout.setSpacing(5)
        self.swatches_layout.addStretch(1)
        self.swatches_scroll.setWidget(self.swatches_container)

        grid_style.addWidget(lbl_swatches, 5, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_style.addWidget(self.swatches_scroll, 5, 1)

        layout_style.addLayout(grid_style)
        self.content_layout.addWidget(card_style)

        # Card 3: Advanced Options (Collapsible)
        card_adv, layout_adv = self._create_card(None)

        self.btn_toggle_adv = QPushButton(self.tr("▶  Advanced Options (Attributes & Folders)"))
        self.btn_toggle_adv.setObjectName("toggleAdvancedBtn")
        self.btn_toggle_adv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_adv.clicked.connect(self._toggle_advanced)
        layout_adv.addWidget(self.btn_toggle_adv)

        self.frame_adv_content = QFrame()
        self.frame_adv_content.setVisible(False)
        layout_adv_inner = QVBoxLayout(self.frame_adv_content)
        layout_adv_inner.setContentsMargins(0, 6, 0, 0)
        layout_adv_inner.setSpacing(10)

        # Group by category folder
        self.chk_group_folder = QCheckBox(self.tr("Group placemarks into Google Earth Folders by category"))
        self.chk_group_folder.setChecked(False)
        layout_adv_inner.addWidget(self.chk_group_folder)

        # ExtendedData attributes
        lbl_extra = QLabel(self.tr("Export attributes (ExtendedData popups):"))
        lbl_extra.setStyleSheet("font-weight: 600;")
        layout_adv_inner.addWidget(lbl_extra)

        h_attr_tools = QHBoxLayout()
        h_attr_tools.setSpacing(6)
        self.txt_field_filter = QLineEdit()
        self.txt_field_filter.setPlaceholderText(self.tr("Filter attributes..."))
        self.txt_field_filter.textChanged.connect(self._filter_field_list)

        btn_select_all = QPushButton(self.tr("Select All"))
        btn_select_all.setProperty("class", "SmallActionBtn")
        btn_select_all.clicked.connect(lambda: self._set_all_fields_checked(True))

        btn_deselect_all = QPushButton(self.tr("Deselect All"))
        btn_deselect_all.setProperty("class", "SmallActionBtn")
        btn_deselect_all.clicked.connect(lambda: self._set_all_fields_checked(False))

        h_attr_tools.addWidget(self.txt_field_filter, 1)
        h_attr_tools.addWidget(btn_select_all)
        h_attr_tools.addWidget(btn_deselect_all)
        layout_adv_inner.addLayout(h_attr_tools)

        self.lst_fields = QListWidget()
        self.lst_fields.setFixedHeight(115)
        layout_adv_inner.addWidget(self.lst_fields)

        layout_adv.addWidget(self.frame_adv_content)
        self.content_layout.addWidget(card_adv)

        # Card 4: Output File
        card_file, layout_file = self._create_card(self.tr("3. Output File"))
        grid_file = QGridLayout()
        grid_file.setContentsMargins(0, 4, 0, 0)
        grid_file.setHorizontalSpacing(12)
        grid_file.setVerticalSpacing(8)
        grid_file.setColumnMinimumWidth(0, self.LABEL_COL_WIDTH)
        grid_file.setColumnStretch(1, 1)

        # Format selector: KMZ vs KML
        lbl_fmt = QLabel(self.tr("File format:"))
        lbl_fmt.setProperty("class", "FormLabel")

        h_fmt = QHBoxLayout()
        h_fmt.setContentsMargins(0, 0, 0, 0)
        h_fmt.setSpacing(16)
        self.rdo_fmt_kmz = QRadioButton(self.tr("KMZ (.kmz - Compressed, recommended)"))
        self.rdo_fmt_kml = QRadioButton(self.tr("KML (.kml - Plain text)"))
        self.rdo_fmt_kmz.setChecked(True)
        self.rdo_fmt_kmz.toggled.connect(self._on_format_changed)
        h_fmt.addWidget(self.rdo_fmt_kmz)
        h_fmt.addWidget(self.rdo_fmt_kml)
        h_fmt.addStretch(1)

        grid_file.addWidget(lbl_fmt, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_file.addLayout(h_fmt, 0, 1)

        # Save destination
        lbl_path = QLabel(self.tr("Save path:"))
        lbl_path.setProperty("class", "FormLabel")

        h_path = QHBoxLayout()
        h_path.setContentsMargins(0, 0, 0, 0)
        h_path.setSpacing(6)
        self.txt_path = QLineEdit()
        self.txt_path.textChanged.connect(self._validate_path)

        btn_browse = QPushButton(self.tr("Browse..."))
        btn_browse.clicked.connect(self._on_browse)

        h_path.addWidget(self.txt_path, 1)
        h_path.addWidget(btn_browse)

        grid_file.addWidget(lbl_path, 1, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid_file.addLayout(h_path, 1, 1)

        self.lbl_path_error = QLabel()
        self.lbl_path_error.setObjectName("errorLabel")
        self.lbl_path_error.setVisible(False)
        grid_file.addWidget(self.lbl_path_error, 2, 1)

        layout_file.addLayout(grid_file)
        self.content_layout.addWidget(card_file)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, 1)

        # Footer Frame
        footer_frame = QFrame()
        footer_frame.setObjectName("footerFrame")
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.setSpacing(10)

        # Progress bar & cancel
        self.progress_frame = QFrame()
        self.progress_frame.setVisible(False)
        p_layout = QHBoxLayout(self.progress_frame)
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(8)

        self.prg_bar = QProgressBar()
        self.prg_bar.setRange(0, 100)
        self.btn_cancel = QPushButton(self.tr("Cancel"))
        self.btn_cancel.setObjectName("cancelButton")
        self.btn_cancel.clicked.connect(self._on_cancel)
        p_layout.addWidget(self.prg_bar, 1)
        p_layout.addWidget(self.btn_cancel)
        footer_layout.addWidget(self.progress_frame, 1)

        # Action buttons
        self.btn_close = QPushButton(self.tr("Close"))
        self.btn_close.setObjectName("closeButton")
        self.btn_close.clicked.connect(self.close)

        self.btn_export = QPushButton(self.tr("Export"))
        self.btn_export.setObjectName("exportButton")
        self.btn_export.clicked.connect(self._on_export)

        footer_layout.addWidget(self.btn_close)
        footer_layout.addWidget(self.btn_export)

        main_layout.addWidget(footer_frame)

        # Author attribution signature
        lbl_footer_author = QLabel(
            self.tr('Developed by <a href="https://github.com/iitold" style="color: #1976d2; text-decoration: none; font-weight: 600;">iitold</a> '
                    '&bull; <a href="mailto:doancongthanh92@gmail.com" style="color: #1976d2; text-decoration: none;">doancongthanh92@gmail.com</a>')
        )
        lbl_footer_author.setOpenExternalLinks(True)
        lbl_footer_author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer_author.setStyleSheet("font-size: 11px; color: #64748b; padding-top: 2px;")
        main_layout.addWidget(lbl_footer_author)

    def _create_card(self, title: Optional[str]) -> Tuple[QFrame, QVBoxLayout]:
        """Helper to create a visually distinct card frame with unified padding."""
        card = QFrame()
        card.setProperty("class", "CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)
        if title:
            lbl = QLabel(title)
            lbl.setProperty("class", "CardTitle")
            card_layout.addWidget(lbl)
        return card, card_layout

    def _toggle_advanced(self) -> None:
        """Toggle collapsed state of Advanced card."""
        is_visible = self.frame_adv_content.isVisible()
        self.frame_adv_content.setVisible(not is_visible)
        if not is_visible:
            self.btn_toggle_adv.setText(self.tr("▼  Advanced Options (Attributes & Folders)"))
        else:
            self.btn_toggle_adv.setText(self.tr("▶  Advanced Options (Attributes & Folders)"))

    def _populate_layers(self) -> None:
        """Populate combobox with all polygon vector layers from project."""
        self.cbo_layer.blockSignals(True)
        self.cbo_layer.clear()

        polygon_layers: List[QgsVectorLayer] = []
        project = QgsProject.instance()

        for layer in project.mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.isValid():
                if layer.geometryType() == Qgis.GeometryType.Polygon:
                    polygon_layers.append(layer)

        active_layer = self.iface.activeLayer() if self.iface else None
        selected_index = 0

        for idx, lyr in enumerate(polygon_layers):
            self.cbo_layer.addItem(lyr.name(), lyr.id())
            if active_layer and lyr.id() == active_layer.id():
                selected_index = idx

        if polygon_layers:
            self.cbo_layer.setCurrentIndex(selected_index)

        self.cbo_layer.blockSignals(False)
        self._on_layer_changed()

    def _get_current_layer(self) -> Optional[QgsVectorLayer]:
        """Retrieve current selected QgsVectorLayer."""
        layer_id = self.cbo_layer.currentData()
        if not layer_id:
            return None
        lyr = QgsProject.instance().mapLayer(layer_id)
        if isinstance(lyr, QgsVectorLayer) and lyr.isValid():
            return lyr
        return None

    def _on_layer_changed(self) -> None:
        """Handle layer selection change."""
        layer = self._get_current_layer()
        if not layer:
            self.chk_selected.setEnabled(False)
            self.chk_selected.setText(self.tr("Export selected features only"))
            self.cbo_name_field.clear()
            self.lst_fields.clear()
            self._render_swatches()
            self._validate_path()
            return

        sel_count = layer.selectedFeatureCount()
        if sel_count > 0:
            self.chk_selected.setEnabled(True)
            self.chk_selected.setText(self.tr(f"Export selected features only ({sel_count} selected)"))
        else:
            self.chk_selected.setEnabled(False)
            self.chk_selected.setChecked(False)
            self.chk_selected.setText(self.tr("Export selected features only (0)"))

        # Populate NameField combobox
        self.cbo_name_field.clear()
        self.cbo_name_field.addItem(self.tr("[No Name]"), None)
        self.cbo_name_field.addItem(self.tr("[Feature ID]"), "__fid__")

        renderer = layer.renderer()
        cat_attr: Optional[str] = None
        if isinstance(renderer, (QgsCategorizedSymbolRenderer, QgsGraduatedSymbolRenderer)):
            cat_attr = renderer.classAttribute()

        default_name_index = 0
        field_names = [f.name() for f in layer.fields()]
        for i, fname in enumerate(field_names):
            self.cbo_name_field.addItem(fname, fname)
            if cat_attr and fname == cat_attr:
                default_name_index = i + 2

        self.cbo_name_field.setCurrentIndex(default_name_index)

        # Populate ExtendedData fields
        self.lst_fields.clear()
        for fname in field_names:
            item = QListWidgetItem(fname, self.lst_fields)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)

        # Update group_by_category availability
        is_grouped_renderer = isinstance(
            renderer,
            (QgsCategorizedSymbolRenderer, QgsGraduatedSymbolRenderer, QgsRuleBasedRenderer),
        )
        self.chk_group_folder.setEnabled(is_grouped_renderer)
        if not is_grouped_renderer:
            self.chk_group_folder.setChecked(False)

        self._update_default_path(layer.name())
        self._render_swatches()
        self._validate_path()

    def _on_format_changed(self) -> None:
        """Switch file extension between .kmz and .kml when format radio toggles."""
        cur = self.txt_path.text().strip()
        if not cur:
            return
        ext = ".kmz" if self.rdo_fmt_kmz.isChecked() else ".kml"
        base, old_ext = os.path.splitext(cur)
        if old_ext.lower() in (".kml", ".kmz"):
            self.txt_path.setText(base + ext)
        else:
            self.txt_path.setText(cur + ext)

    def _update_default_path(self, layer_name: str) -> None:
        """Update output path field with default Downloads path."""
        last_dir = self.settings.value(self.SETTINGS_PREFIX + "last_dir", "")
        if not last_dir or not os.path.isdir(last_dir):
            last_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        clean_name = "".join(c for c in layer_name if c.isalnum() or c in (" ", "_", "-")).rstrip()
        clean_name = clean_name or "export"
        ext = ".kmz" if self.rdo_fmt_kmz.isChecked() else ".kml"
        default_file = os.path.join(last_dir, f"{clean_name}{ext}")
        self.txt_path.setText(default_file)

    def _render_swatches(self) -> None:
        """Render color chips (swatches) showing category colors and stroke style."""
        new_container = QWidget()
        new_layout = QHBoxLayout(new_container)
        new_layout.setContentsMargins(0, 2, 0, 2)
        new_layout.setSpacing(5)

        layer = self._get_current_layer()
        if not layer:
            new_layout.addStretch(1)
            self.swatches_scroll.setWidget(new_container)
            return

        renderer = layer.renderer()
        if not renderer:
            new_layout.addStretch(1)
            self.swatches_scroll.setWidget(new_container)
            return

        color_list: List[QColor] = []
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            for cat in renderer.categories()[:14]:
                if cat.symbol():
                    color_list.append(cat.symbol().color())
        elif isinstance(renderer, QgsGraduatedSymbolRenderer):
            for rng in renderer.ranges()[:14]:
                if rng.symbol():
                    color_list.append(rng.symbol().color())
        elif isinstance(renderer, QgsRuleBasedRenderer):
            for child in renderer.rootRule().children()[:14]:
                if child.symbol():
                    color_list.append(child.symbol().color())
        else:
            if renderer.symbol():
                color_list.append(renderer.symbol().color())

        # Deduplicate while preserving order and filter invalid colors
        seen_colors = set()
        unique_colors: List[QColor] = []
        for col in color_list:
            if not col or not col.isValid():
                continue
            key = (col.red(), col.green(), col.blue())
            if key not in seen_colors:
                seen_colors.add(key)
                unique_colors.append(col)

        stroke_mode = self._get_stroke_mode()
        alpha_val = (
            int(round(self.sld_alpha.value() * 2.55))
            if not self.chk_alpha_symbol.isChecked()
            else None
        )

        for col in unique_colors:
            chip = QLabel()
            chip.setFixedSize(22, 22)
            pixmap = QPixmap(22, 22)
            pixmap.fill(Qt.GlobalColor.transparent)

            p = QPainter(pixmap)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            fill_c = QColor(col)
            if alpha_val is not None:
                fill_c.setAlpha(alpha_val)

            if stroke_mode == "none":
                stroke_pen = Qt.PenStyle.NoPen
            elif stroke_mode == "same":
                stroke_pen = QPen(fill_c, 1.5)
            elif stroke_mode == "same_opaque":
                op_c = QColor(fill_c.red(), fill_c.green(), fill_c.blue(), 255)
                stroke_pen = QPen(op_c, 1.5)
            else:
                stroke_pen = QPen(QColor(60, 60, 60, 220), 1.5)

            p.setPen(stroke_pen)
            p.setBrush(QBrush(fill_c))
            p.drawRoundedRect(1, 1, 20, 20, 4, 4)
            p.end()

            chip.setPixmap(pixmap)
            new_layout.addWidget(chip)

        new_layout.addStretch(1)
        self.swatches_scroll.setWidget(new_container)

    def _on_stroke_mode_changed(self, checked: bool = True) -> None:
        if not checked:
            return
        self._render_swatches()

    def _on_alpha_symbol_toggled(self, checked: bool) -> None:
        self.sld_alpha.setEnabled(not checked)
        self.lbl_alpha_val.setEnabled(not checked)
        self._render_swatches()

    def _filter_field_list(self, text: str) -> None:
        query = text.lower().strip()
        for idx in range(self.lst_fields.count()):
            item = self.lst_fields.item(idx)
            item.setHidden(query not in item.text().lower())

    def _set_all_fields_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for idx in range(self.lst_fields.count()):
            self.lst_fields.item(idx).setCheckState(state)

    def _on_browse(self) -> None:
        cur_path = self.txt_path.text().strip()
        start_dir = os.path.dirname(cur_path) if cur_path else ""
        filter_str = (
            self.tr("KMZ files (*.kmz);;KML files (*.kml);;All files (*.*)")
            if self.rdo_fmt_kmz.isChecked()
            else self.tr("KML files (*.kml);;KMZ files (*.kmz);;All files (*.*)")
        )
        file_path, sel_filter = QFileDialog.getSaveFileName(
            self,
            self.tr("Save KML/KMZ File"),
            start_dir,
            filter_str,
        )
        if file_path:
            ext = ".kmz" if ("*.kmz" in sel_filter or self.rdo_fmt_kmz.isChecked()) else ".kml"
            if not file_path.lower().endswith((".kml", ".kmz")):
                file_path += ext
            self.txt_path.setText(file_path)
            if file_path.lower().endswith(".kmz"):
                self.rdo_fmt_kmz.setChecked(True)
            elif file_path.lower().endswith(".kml"):
                self.rdo_fmt_kml.setChecked(True)

    def _validate_path(self) -> None:
        path = self.txt_path.text().strip()
        layer = self._get_current_layer()

        if not layer:
            self.lbl_path_error.setText(self.tr("Please select a polygon layer."))
            self.lbl_path_error.setVisible(True)
            self.btn_export.setEnabled(False)
            return

        if not path:
            self.lbl_path_error.setText(self.tr("Please specify a valid save path."))
            self.lbl_path_error.setVisible(True)
            self.btn_export.setEnabled(False)
            return

        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            self.lbl_path_error.setText(self.tr("Destination folder does not exist."))
            self.lbl_path_error.setVisible(True)
            self.btn_export.setEnabled(False)
            return

        self.lbl_path_error.setVisible(False)
        self.btn_export.setEnabled(True)

    def _get_stroke_mode(self) -> str:
        if self.rdo_stroke_opaque.isChecked():
            return "same_opaque"
        elif self.rdo_stroke_orig.isChecked():
            return "original"
        elif self.rdo_stroke_none.isChecked():
            return "none"
        return "same"

    def _get_export_options(self) -> ExportOptions:
        out_path = self.txt_path.text().strip()
        default_ext = ".kmz" if self.rdo_fmt_kmz.isChecked() else ".kml"
        if not out_path.lower().endswith((".kml", ".kmz")):
            out_path += default_ext

        name_field = self.cbo_name_field.currentData()

        extra_fields: List[str] = []
        for idx in range(self.lst_fields.count()):
            item = self.lst_fields.item(idx)
            if item.checkState() == Qt.CheckState.Checked:
                extra_fields.append(item.text())

        stroke_mode = self._get_stroke_mode()
        stroke_width = (
            None if self.chk_stroke_symbol.isChecked() else float(self.spn_stroke_width.value())
        )
        fill_alpha = (
            None if self.chk_alpha_symbol.isChecked() else float(self.sld_alpha.value() / 100.0)
        )

        scale_factor = float(self.spn_scale.value()) / 100.0
        scale_anchor = self.cbo_scale_anchor.currentData() or "first_vertex"

        return ExportOptions(
            out_path=out_path,
            name_field=name_field,
            extra_fields=extra_fields,
            only_selected=self.chk_selected.isChecked(),
            stroke_mode=stroke_mode,
            stroke_width=stroke_width,
            group_by_category=self.chk_group_folder.isChecked(),
            fill_alpha=fill_alpha,
            scale_factor=scale_factor,
            scale_anchor=scale_anchor,
        )

    def _save_settings(self) -> None:
        self.settings.setValue(self.SETTINGS_PREFIX + "stroke_mode", self._get_stroke_mode())
        self.settings.setValue(
            self.SETTINGS_PREFIX + "stroke_from_symbol", self.chk_stroke_symbol.isChecked()
        )
        self.settings.setValue(
            self.SETTINGS_PREFIX + "stroke_width", float(self.spn_stroke_width.value())
        )
        self.settings.setValue(
            self.SETTINGS_PREFIX + "alpha_from_symbol", self.chk_alpha_symbol.isChecked()
        )
        self.settings.setValue(self.SETTINGS_PREFIX + "alpha_value", int(self.sld_alpha.value()))
        self.settings.setValue(
            self.SETTINGS_PREFIX + "group_by_category", self.chk_group_folder.isChecked()
        )
        self.settings.setValue(
            self.SETTINGS_PREFIX + "format", "kmz" if self.rdo_fmt_kmz.isChecked() else "kml"
        )
        self.settings.setValue(self.SETTINGS_PREFIX + "scale_factor", int(self.spn_scale.value()))
        self.settings.setValue(
            self.SETTINGS_PREFIX + "scale_anchor", self.cbo_scale_anchor.currentData()
        )

        cur_path = self.txt_path.text().strip()
        if cur_path:
            self.settings.setValue(self.SETTINGS_PREFIX + "last_dir", os.path.dirname(cur_path))

    def _load_settings(self) -> None:
        mode = self.settings.value(self.SETTINGS_PREFIX + "stroke_mode", "same")
        if mode == "same_opaque":
            self.rdo_stroke_opaque.setChecked(True)
        elif mode == "original":
            self.rdo_stroke_orig.setChecked(True)
        elif mode == "none":
            self.rdo_stroke_none.setChecked(True)
        else:
            self.rdo_stroke_same.setChecked(True)

        stroke_sym = self.settings.value(self.SETTINGS_PREFIX + "stroke_from_symbol", False, type=bool)
        self.chk_stroke_symbol.setChecked(stroke_sym)
        self.spn_stroke_width.setEnabled(not stroke_sym)

        stroke_w = self.settings.value(self.SETTINGS_PREFIX + "stroke_width", 1.0, type=float)
        self.spn_stroke_width.setValue(stroke_w)

        alpha_sym = self.settings.value(self.SETTINGS_PREFIX + "alpha_from_symbol", True, type=bool)
        self.chk_alpha_symbol.setChecked(alpha_sym)
        self.sld_alpha.setEnabled(not alpha_sym)
        self.lbl_alpha_val.setEnabled(not alpha_sym)

        alpha_v = self.settings.value(self.SETTINGS_PREFIX + "alpha_value", 80, type=int)
        self.sld_alpha.setValue(alpha_v)
        self.lbl_alpha_val.setText(f"{alpha_v}%")

        group_cat = self.settings.value(self.SETTINGS_PREFIX + "group_by_category", False, type=bool)
        if self.chk_group_folder.isEnabled():
            self.chk_group_folder.setChecked(group_cat)

        fmt = self.settings.value(self.SETTINGS_PREFIX + "format", "kmz")
        if fmt == "kml":
            self.rdo_fmt_kml.setChecked(True)
        else:
            self.rdo_fmt_kmz.setChecked(True)

        scale_val = self.settings.value(self.SETTINGS_PREFIX + "scale_factor", 100, type=int)
        self.spn_scale.setValue(scale_val)

        anchor_val = self.settings.value(self.SETTINGS_PREFIX + "scale_anchor", "first_vertex")
        idx = self.cbo_scale_anchor.findData(anchor_val)
        if idx >= 0:
            self.cbo_scale_anchor.setCurrentIndex(idx)

    def _update_ui_state(self) -> None:
        self._validate_path()

    def _on_export(self) -> None:
        layer = self._get_current_layer()
        if not layer:
            return

        options = self._get_export_options()
        self._save_settings()

        self.btn_export.setEnabled(False)
        self.btn_close.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.prg_bar.setValue(0)

        self.current_task = KmlExportTask(
            description=f"qgis2ge Export ({layer.name()})",
            layer=layer,
            options=options,
            on_finished=self._on_task_finished,
        )
        self.current_task.progressChanged.connect(self._on_task_progress)

        QgsApplication.taskManager().addTask(self.current_task)

    def _on_task_progress(self, progress: float) -> None:
        self.prg_bar.setValue(int(progress))

    def _on_cancel(self) -> None:
        if self.current_task:
            self.current_task.cancel()

    def _on_task_finished(self, result: ExportResult) -> None:
        self.current_task = None
        self.progress_frame.setVisible(False)
        self.btn_export.setEnabled(True)
        self.btn_close.setEnabled(True)

        if not self.iface:
            return

        msg_bar = self.iface.messageBar()

        if result.canceled:
            msg_bar.pushWarning(
                self.tr("qgis2ge"),
                self.tr("Export process was canceled by user."),
            )
            return

        if result.warnings and result.exported_count == 0:
            err_msg = "; ".join(result.warnings)
            msg_bar.pushCritical(
                self.tr("qgis2ge Export Failed"),
                self.tr(f"Could not export file: {err_msg}"),
            )
            return

        ext_label = "KMZ" if result.output_path.lower().endswith(".kmz") else "KML"
        success_text = self.tr(
            f"Successfully exported {result.exported_count} feature(s) to {ext_label}."
        )
        if result.skipped_count > 0:
            success_text += self.tr(f" ({result.skipped_count} empty/invalid geometries skipped).")

        widget = msg_bar.createMessage(self.tr("qgis2ge"), success_text)
        btn_open = QPushButton(self.tr("Open Folder"))
        folder_path = os.path.dirname(result.output_path)

        def open_folder():
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

        btn_open.clicked.connect(open_folder)
        widget.layout().addWidget(btn_open)

        msg_bar.pushWidget(widget, Qgis.MessageLevel.Success, duration=10)

        self.accept()

    def _on_check_update(self) -> None:
        """Trigger update check or execute pending update/reload action without layout shift."""
        # Case 1: An update is available and user clicks the update button
        if self.latest_update_info and self.latest_update_info.has_update and "Update" in self.btn_check_update.text():
            new_v = self.latest_update_info.latest_version
            msg = (
                f"A new version v{new_v} of qgis2ge is available!\n"
                f"(Your current version: v{self.current_version})\n\n"
            )
            if self.latest_update_info.changelog:
                msg += f"Release Notes:\n{self.latest_update_info.changelog.strip()}\n\n"
            msg += "Do you want to download and install this update now?"

            reply = QMessageBox.question(
                self,
                self.tr("qgis2ge Update Available"),
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_apply_update()
            return

        # Case 2: Update was installed and user clicks Reload Plugin
        if "Reload" in self.btn_check_update.text():
            self._on_reload_and_close()
            return

        # Case 3: Initial Check
        self.btn_check_update.setText(self.tr("Checking..."))
        self.btn_check_update.setEnabled(False)

        self.check_update_task = CheckUpdateTask(
            repo="iitold/qgis2ge",
            current_version=self.current_version,
            on_completed=self._on_check_update_completed,
        )
        QgsApplication.taskManager().addTask(self.check_update_task)

    def _on_check_update_completed(self, info: UpdateInfo) -> None:
        """Handle results of update check with zero layout shift."""
        self.latest_update_info = info
        self.btn_check_update.setEnabled(True)

        if info.error_message:
            self.btn_check_update.setText(self.tr("Check Failed"))
            QTimer.singleShot(3000, lambda: self.btn_check_update.setText(self.tr("Check for Updates")))
            if self.iface:
                self.iface.messageBar().pushWarning(self.tr("qgis2ge"), self.tr(f"Update check: {info.error_message}"))
            return

        if info.has_update:
            self.btn_check_update.setText(self.tr(f"★ Update to v{info.latest_version}"))
            self.btn_check_update.setStyleSheet(
                "background-color: #2E7D32; color: #FFFFFF; font-weight: 700; border: none; border-radius: 10px; padding: 2px 10px;"
            )
            if self.iface:
                self.iface.messageBar().pushInfo(
                    self.tr("qgis2ge"),
                    self.tr(f"New version v{info.latest_version} available! Click 'Update to v{info.latest_version}' in the dialog."),
                    duration=6,
                )
        else:
            self.btn_check_update.setText(self.tr("✓ Up to date"))
            QTimer.singleShot(3500, lambda: self.btn_check_update.setText(self.tr("Check for Updates")))

    def _on_apply_update(self) -> None:
        """Download and install the latest update in background."""
        if not self.latest_update_info or not self.latest_update_info.download_url:
            return

        self.btn_check_update.setText(self.tr("Downloading..."))
        self.btn_check_update.setEnabled(False)

        self.install_update_task = InstallUpdateTask(
            download_url=self.latest_update_info.download_url,
            on_completed=self._on_install_completed,
        )
        QgsApplication.taskManager().addTask(self.install_update_task)

    def _on_install_completed(self, success: bool, message: str) -> None:
        """Handle update installation result on the main GUI thread."""
        self.btn_check_update.setEnabled(True)
        if success:
            new_ver = self.latest_update_info.latest_version if self.latest_update_info else self.current_version
            self.current_version = new_ver
            self.lbl_version_badge.setText(f"v{self.current_version}")
            self.btn_check_update.setText(self.tr("Reload Plugin"))
            self.btn_check_update.setStyleSheet(
                "background-color: #1976D2; color: #FFFFFF; font-weight: 700; border: none; border-radius: 10px; padding: 2px 10px;"
            )
            QMessageBox.information(
                self,
                self.tr("Update Installed"),
                self.tr(f"qgis2ge has been updated to v{new_ver} successfully!\n\nClick 'Reload Plugin' or restart QGIS to apply the new version."),
            )
        else:
            self.btn_check_update.setText(self.tr("Update Failed"))
            self.btn_check_update.setStyleSheet("")
            QMessageBox.warning(self, self.tr("Update Failed"), self.tr(f"Installation failed: {message}"))
            QTimer.singleShot(4000, lambda: self.btn_check_update.setText(self.tr("Check for Updates")))

    def _perform_clean_reload(self, reopen_dialog: bool = False) -> bool:
        """Purge all cached submodules from RAM and reload freshly from disk via QGIS unload/load cycle."""
        import sys
        import qgis.utils

        pkg = "qgis2ge"

        # 1. Gracefully unload plugin via official QGIS API
        if pkg in qgis.utils.active_plugins:
            qgis.utils.unloadPlugin(pkg)
        elif pkg in qgis.utils.plugins:
            try:
                qgis.utils.plugins[pkg].unload()
            except Exception as exc:
                _ = exc
            del qgis.utils.plugins[pkg]

        if pkg in qgis.utils.active_plugins:
            qgis.utils.active_plugins.remove(pkg)

        # 2. PURGE all cached qgis2ge submodules from Python sys.modules
        cached_modules = [
            m for m in list(sys.modules.keys())
            if m == pkg or m.startswith(pkg + ".")
        ]
        for m in cached_modules:
            del sys.modules[m]

        sys.path_importer_cache.clear()

        # 3. Clean load and start
        qgis.utils.loadPlugin(pkg)
        started = qgis.utils.startPlugin(pkg)

        # 4. Optionally re-open dialog if plugin started successfully
        if reopen_dialog and started and pkg in qgis.utils.plugins:
            qgis.utils.plugins[pkg].run()

        return started

    def _on_reload_and_close(self) -> None:
        """Close dialog and trigger a true, complete hot-reload on the next Qt main loop iteration."""
        # Close the modal dialog so QGIS event loop is completely free
        self.close()

        def do_reload():
            try:
                self._perform_clean_reload(reopen_dialog=False)
                if self.iface:
                    self.iface.messageBar().pushSuccess(
                        self.tr("qgis2ge"),
                        self.tr(f"qgis2ge v{self.current_version} hot-reloaded successfully! All modules refreshed."),
                    )
            except Exception as e:
                if self.iface:
                    self.iface.messageBar().pushWarning(
                        self.tr("qgis2ge"),
                        self.tr(f"Update applied to disk. Please restart QGIS to finalize: {e}"),
                    )

        QTimer.singleShot(250, do_reload)

    def _on_clean_reload(self) -> None:
        """Purge all cached submodules from RAM and reload freshly from disk, then re-open dialog."""
        self.close()

        def do_clean_reload():
            try:
                self._perform_clean_reload(reopen_dialog=True)
                if self.iface:
                    self.iface.messageBar().pushSuccess(
                        self.tr("qgis2ge"),
                        self.tr("Plugin freshly reloaded from disk! UI refreshed."),
                    )
            except Exception as e:
                if self.iface:
                    self.iface.messageBar().pushWarning(
                        self.tr("qgis2ge"),
                        self.tr(f"Reload notice: Please restart QGIS: {e}"),
                    )

        QTimer.singleShot(250, do_clean_reload)
