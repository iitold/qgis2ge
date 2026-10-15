"""qgis2ge (QGIS to Google Earth) Plugin.

Exports polygon layers to styled KML or compressed KMZ maintaining fill color,
stroke color, width, opacity, and custom size scaling for Google Earth.
"""

from typing import Any


def classFactory(iface: Any) -> Any:
    """Entry point invoked by QGIS Plugin Manager to instantiate the plugin.

    Args:
        iface: QGIS interface instance (QgisInterface).

    Returns:
        Qgis2GePlugin instance.
    """
    from qgis2ge.plugin import Qgis2GePlugin

    return Qgis2GePlugin(iface)
