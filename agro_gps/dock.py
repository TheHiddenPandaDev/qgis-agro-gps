from __future__ import annotations

from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox, QgsMapToolEmitPoint
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import layers
from .core.client import AgroGpsClient, sigpac_parcel_at
from .core.errors import AgroGpsError
from .core.export import field_payload
from .core.parsing import fields_from_records, sigpac_from_feature
from .core.presentation import format_area
from .i18n import tr
from .qgis_transport import qgis_transport
from .settings_store import load_country, load_credential, load_farm, save_country, save_credential, save_farm

KEYS_HELP_URL = "https://agrogps.eu/en/developers/"
WGS84 = "EPSG:4326"
NAME_FIELD = "name"


class AgroGpsDock(QDockWidget):
    def __init__(self, iface, parent=None) -> None:
        super().__init__(tr("Agro GPS"), parent)
        self.iface = iface
        self.setObjectName("AgroGpsDock")
        self.map_tool: QgsMapToolEmitPoint | None = None
        self.previous_tool = None
        root = QWidget()
        column = QVBoxLayout(root)
        column.addWidget(self._key_box())
        column.addWidget(self._fields_box())
        column.addWidget(self._sigpac_box())
        column.addWidget(self._export_box())
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        column.addWidget(self.status)
        column.addStretch(1)
        self.setWidget(root)

    def _key_box(self) -> QGroupBox:
        box = QGroupBox(tr("Agro GPS key"))
        form = QFormLayout(box)
        self.credential_edit = QLineEdit(load_credential())
        self.credential_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.credential_edit.setPlaceholderText(tr("Paste the key from Agro GPS > Settings > API and webhooks"))
        save = QPushButton(tr("Save key"))
        save.clicked.connect(self.save_key)
        row = QHBoxLayout()
        row.addWidget(self.credential_edit)
        row.addWidget(save)
        form.addRow(row)
        link = QLabel(f'<a href="{KEYS_HELP_URL}">{tr("How to create a key")}</a>')
        link.setOpenExternalLinks(True)
        form.addRow(link)
        return box

    def _fields_box(self) -> QGroupBox:
        box = QGroupBox(tr("My fields"))
        form = QFormLayout(box)
        self.farm_combo = QComboBox()
        refresh = QPushButton(tr("Load farms"))
        refresh.clicked.connect(self.load_farms)
        row = QHBoxLayout()
        row.addWidget(self.farm_combo, 1)
        row.addWidget(refresh)
        form.addRow(tr("Farm"), row)
        load = QPushButton(tr("Load my fields as a layer"))
        load.clicked.connect(self.load_fields)
        form.addRow(load)
        return box

    def _sigpac_box(self) -> QGroupBox:
        box = QGroupBox(tr("SIGPAC parcel (Spain)"))
        form = QFormLayout(box)
        pick = QPushButton(tr("Pick a point on the map"))
        pick.clicked.connect(self.start_pick)
        form.addRow(pick)
        self.lat_edit = QLineEdit()
        self.lon_edit = QLineEdit()
        self.lat_edit.setPlaceholderText("40.4168")
        self.lon_edit.setPlaceholderText("-3.7038")
        search = QPushButton(tr("Search"))
        search.clicked.connect(self.search_point)
        row = QHBoxLayout()
        row.addWidget(self.lat_edit)
        row.addWidget(self.lon_edit)
        row.addWidget(search)
        form.addRow(tr("Lat, lon"), row)
        return box

    def _export_box(self) -> QGroupBox:
        box = QGroupBox(tr("Send polygons to my notebook"))
        form = QFormLayout(box)
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.PolygonLayer)
        self.name_combo = QgsFieldComboBox()
        self.layer_combo.layerChanged.connect(self._layer_changed)
        self._layer_changed(self.layer_combo.currentLayer())
        self.country_edit = QLineEdit(load_country())
        self.country_edit.setMaxLength(2)
        form.addRow(tr("Layer"), self.layer_combo)
        form.addRow(tr("Name field"), self.name_combo)
        form.addRow(tr("Country"), self.country_edit)
        send = QPushButton(tr("Send selected polygons"))
        send.clicked.connect(self.send_selection)
        form.addRow(send)
        return box

    def _layer_changed(self, layer) -> None:
        self.name_combo.setLayer(layer)
        if layer is not None and layer.fields().indexOf(NAME_FIELD) >= 0:
            self.name_combo.setField(NAME_FIELD)

    def _client(self) -> AgroGpsClient:
        return AgroGpsClient(self.credential_edit.text(), transport=qgis_transport)

    def _report(self, message: str, level=Qgis.MessageLevel.Info) -> None:
        self.status.setText(message)
        self.iface.messageBar().pushMessage(tr("Agro GPS"), message, level=level, duration=6)

    def _fail(self, error: Exception) -> None:
        self._report(str(error), Qgis.MessageLevel.Warning)

    def save_key(self) -> None:
        save_credential(self.credential_edit.text())
        self._report(tr("Key saved in your QGIS profile."))

    def load_farms(self) -> None:
        try:
            farms = self._client().farms()
        except AgroGpsError as error:
            self._fail(error)
            return
        self.farm_combo.clear()
        for farm in farms:
            self.farm_combo.addItem(f'{farm.get("name") or farm["id"]} ({farm.get("country") or ""})', farm["id"])
        remembered = self.farm_combo.findData(load_farm())
        if remembered >= 0:
            self.farm_combo.setCurrentIndex(remembered)
        self._report(tr("{n} farms.").format(n=len(farms)))

    def _farm_id(self) -> str:
        farm_id = self.farm_combo.currentData() or ""
        if not farm_id:
            raise AgroGpsError(tr("Load your farms and choose one first."))
        save_farm(farm_id)
        return farm_id

    def load_fields(self) -> None:
        project = QgsProject.instance()
        try:
            fields = fields_from_records(self._client().parcel_records(self._farm_id()))
        except AgroGpsError as error:
            self._fail(error)
            return
        layer = layers.fields_layer(project)
        count = layers.replace_fields(layer, fields)
        if count:
            layers.ensure_basemap(project)
            layers.frame(project, self.iface.mapCanvas(), layer.extent())
        self._report(tr("{n} fields with an outline loaded.").format(n=count))

    def start_pick(self) -> None:
        canvas = self.iface.mapCanvas()
        self.previous_tool = canvas.mapTool()
        self.map_tool = QgsMapToolEmitPoint(canvas)
        self.map_tool.canvasClicked.connect(self._picked)
        canvas.setMapTool(self.map_tool)
        self._report(tr("Click on the map to look up the SIGPAC parcel."))

    def _picked(self, point, _button) -> None:
        canvas = self.iface.mapCanvas()
        transform = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(),
                                           QgsCoordinateReferenceSystem(WGS84), QgsProject.instance())
        wgs = transform.transform(point)
        if self.previous_tool is not None:
            canvas.setMapTool(self.previous_tool)
        self.lat_edit.setText(f"{wgs.y():.6f}")
        self.lon_edit.setText(f"{wgs.x():.6f}")
        self.lookup(wgs.y(), wgs.x())

    def search_point(self) -> None:
        try:
            lat = float(self.lat_edit.text().replace(",", "."))
            lon = float(self.lon_edit.text().replace(",", "."))
        except ValueError:
            self._report(tr("Type latitude and longitude as numbers."), Qgis.MessageLevel.Warning)
            return
        self.lookup(lat, lon)

    def lookup(self, lat: float, lon: float) -> None:
        project = QgsProject.instance()
        try:
            parcel = sigpac_from_feature(sigpac_parcel_at(qgis_transport, lat, lon))
        except AgroGpsError as error:
            self._fail(error)
            return
        if parcel is None:
            self._report(tr("SIGPAC returned a parcel without an outline."), Qgis.MessageLevel.Warning)
            return
        layer = layers.sigpac_layer(project)
        feature = layers.add_sigpac(layer, parcel)
        layers.ensure_basemap(project)
        layers.frame(project, self.iface.mapCanvas(), feature.geometry().boundingBox())
        self._report(f"{parcel.reference} · {parcel.land_use} · {format_area(parcel.area_ha)}")

    def send_selection(self) -> None:
        layer = self.layer_combo.currentLayer()
        name_field = self.name_combo.currentField()
        country = self.country_edit.text().strip().upper()
        if layer is None or not layer.selectedFeatureCount():
            self._report(tr("Select one or more polygons in the layer first."), Qgis.MessageLevel.Warning)
            return
        try:
            payloads = []
            for feature in layer.selectedFeatures():
                name = str(feature[name_field]) if name_field else ""
                ring = layers.outer_ring_lon_lat(feature.geometry(), layer.crs(), QgsProject.instance())
                payloads.append(field_payload(name or tr("Field {id}").format(id=feature.id()), country, ring))
            saved = self._client().import_fields(self._farm_id(), payloads)
        except AgroGpsError as error:
            self._fail(error)
            return
        save_country(country)
        accepted = [f for f in saved if f.get("result") == "accepted"]
        self._report(tr("{ok} of {n} fields saved in your notebook.").format(ok=len(accepted), n=len(payloads)))

    def shutdown(self) -> None:
        canvas = self.iface.mapCanvas()
        if self.map_tool is not None and canvas.mapTool() is self.map_tool:
            canvas.unsetMapTool(self.map_tool)
        self.map_tool = None
