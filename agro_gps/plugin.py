from __future__ import annotations

import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dock import AgroGpsDock
from .i18n import tr

ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png")
MENU = "&Agro GPS"


class AgroGpsPlugin:
    def __init__(self, iface) -> None:
        self.iface = iface
        self.action: QAction | None = None
        self.dock: AgroGpsDock | None = None

    def initGui(self) -> None:
        self.action = QAction(QIcon(ICON_PATH), tr("Agro GPS - farm fields and SIGPAC"), self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.setToolTip(tr("Your Agro GPS fields, SIGPAC parcels and sending polygons to your notebook"))
        self.action.toggled.connect(self._toggle_dock)
        self.iface.addWebToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(MENU, self.action)

    def unload(self) -> None:
        if self.dock is not None:
            self.dock.shutdown()
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        if self.action is not None:
            self.iface.removeWebToolBarIcon(self.action)
            self.iface.removePluginWebMenu(MENU, self.action)
            self.action = None

    def _toggle_dock(self, visible: bool) -> None:
        if self.dock is None:
            self.dock = AgroGpsDock(self.iface, self.iface.mainWindow())
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
            self.dock.visibilityChanged.connect(self._sync_action)
        self.dock.setVisible(visible)
        if visible:
            self.dock.prepare_view()

    def _sync_action(self, visible: bool) -> None:
        if self.action is not None and self.action.isChecked() != visible:
            self.action.setChecked(visible)
