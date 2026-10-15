"""Background QgsTask for asynchronous KML/KMZ export in qgis2ge."""

from __future__ import annotations

import os
from typing import Callable, Optional

from qgis.core import QgsTask, QgsVectorLayer

from qgis2ge.exporter import ExportOptions, ExportResult, export_kml


class KmlExportTask(QgsTask):
    """QgsTask executing export_kml in a background worker thread."""

    def __init__(
        self,
        description: str,
        layer: QgsVectorLayer,
        options: ExportOptions,
        on_finished: Optional[Callable[[ExportResult], None]] = None,
    ):
        super().__init__(description, QgsTask.CanCancel)
        self.layer = layer
        self.options = options
        self.on_finished = on_finished
        self.result: Optional[ExportResult] = None
        self.exception: Optional[Exception] = None

    def run(self) -> bool:
        """Run export in background thread."""
        try:
            self.result = export_kml(self.layer, self.options, feedback=self)
            if self.isCanceled() or (self.result and self.result.canceled):
                return False
            return True
        except Exception as e:
            self.exception = e
            return False

    def finished(self, result: bool) -> None:
        """Executed in GUI thread upon task completion or cancellation."""
        if self.isCanceled():
            if os.path.exists(self.options.out_path):
                try:
                    os.remove(self.options.out_path)
                except OSError:
                    pass

        if self.result is None:
            self.result = ExportResult(
                exported_count=0,
                skipped_count=0,
                output_path=self.options.out_path,
                warnings=[str(self.exception)] if self.exception else ["Export process was canceled."],
                canceled=self.isCanceled(),
            )

        if self.on_finished:
            self.on_finished(self.result)

    def cancel(self) -> None:
        """User requested task cancellation."""
        super().cancel()
        if os.path.exists(self.options.out_path):
            try:
                os.remove(self.options.out_path)
            except OSError:
                pass
