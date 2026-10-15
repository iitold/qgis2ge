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

        self.reload_action = QAction(self.tr("qgis2ge: Clean Reload Plugin"), self.iface.mainWindow())
        self.reload_action.setObjectName("qgis2geReloadAction")
        self.reload_action.setStatusTip(
            self.tr("Purge RAM module cache and reload qgis2ge freshly from disk without restarting QGIS")
        )
        self.reload_action.triggered.connect(self.clean_reload)

        # Add to Vector menu and Vector toolbar
        self.iface.addPluginToVectorMenu(self.tr("&qgis2ge"), self.action)
        self.iface.addPluginToVectorMenu(self.tr("&qgis2ge"), self.reload_action)
        self.iface.addVectorToolBarIcon(self.action)

    def unload(self) -> None:
        """Tear down GUI items when plugin is uninstalled or reloaded."""
        if self.action is not None:
            self.iface.removePluginVectorMenu(self.tr("&qgis2ge"), self.action)
            self.iface.removeVectorToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

        if self.reload_action is not None:
            self.iface.removePluginVectorMenu(self.tr("&qgis2ge"), self.reload_action)
            self.reload_action.deleteLater()
            self.reload_action = None

        if self.dlg is not None:
            self.dlg.close()
            self.dlg = None

    def clean_reload(self) -> None:
        """Purge all cached submodules from RAM and reload freshly from disk."""
        import sys
        import qgis.utils
        from qgis.PyQt.QtCore import QTimer

        def do_reload():
            try:
                pkg = "qgis2ge"
                if pkg in qgis.utils.active_plugins:
                    qgis.utils.unloadPlugin(pkg)
                elif pkg in qgis.utils.plugins:
                    try:
                        qgis.utils.plugins[pkg].unload()
                    except Exception:
                        pass
                    del qgis.utils.plugins[pkg]

                if pkg in qgis.utils.active_plugins:
                    qgis.utils.active_plugins.remove(pkg)

                cached = [m for m in list(sys.modules.keys()) if m == pkg or m.startswith(pkg + ".")]
                for m in cached:
                    del sys.modules[m]

                sys.path_importer_cache.clear()

                qgis.utils.loadPlugin(pkg)
                qgis.utils.startPlugin(pkg)

                if self.iface:
                    self.iface.messageBar().pushSuccess("qgis2ge", "Plugin cleanly reloaded from disk!")
            except Exception as e:
                if self.iface:
                    self.iface.messageBar().pushWarning("qgis2ge", f"Reload notice: Please restart QGIS: {e}")

        QTimer.singleShot(150, do_reload)

    def run(self) -> None:
        """Display the export configuration dialog."""
        self.dlg = Qgis2GeDialog(self.iface, self.iface.mainWindow())
        self.dlg.exec_()
