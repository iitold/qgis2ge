"""Main entry and QGIS GUI integration for qgis2ge plugin."""

from __future__ import annotations

import os
from typing import Any, Optional

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis2ge.dialog import Qgis2GeDialog


class Qgis2GePlugin:
    """Plugin controller managing QGIS GUI integration and dialog lifecycle."""

    def __init__(self, iface: Any):
        self.iface = iface
        self.action: Optional[QAction] = None
        self.dlg: Optional[Qgis2GeDialog] = None
        self.plugin_dir = os.path.dirname(__file__)

    def tr(self, message: str) -> str:
        """Translate message using QCoreApplication."""
        return QCoreApplication.translate("Qgis2GePlugin", message)

    def initGui(self) -> None:
        """Register toolbar icons and menu items in QGIS."""
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        self.action = QAction(icon, self.tr("qgis2ge: Export to Google Earth..."), self.iface.mainWindow())
        self.action.setObjectName("qgis2geAction")
        self.action.setStatusTip(
            self.tr("Export polygon layers to KML/KMZ preserving styles, colors, opacity, and scale for Google Earth")
        )
        self.action.triggered.connect(self.run)

        # Add to Vector menu and Vector toolbar
        self.iface.addPluginToVectorMenu(self.tr("&qgis2ge"), self.action)
        self.iface.addVectorToolBarIcon(self.action)

    def unload(self) -> None:
        """Tear down GUI items when plugin is uninstalled or reloaded."""
        if self.action is not None:
            self.iface.removePluginVectorMenu(self.tr("&qgis2ge"), self.action)
            self.iface.removeVectorToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

        if self.dlg is not None:
            self.dlg.close()
            self.dlg = None

    def run(self) -> None:
        """Display the export configuration dialog."""
        self.dlg = Qgis2GeDialog(self.iface, self.iface.mainWindow())
        self.dlg.exec_()
