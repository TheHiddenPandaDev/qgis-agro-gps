from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

SQUARE_METRES_PER_HECTARE = 10_000
HECTARE_DECIMALS = 2
ZOOM_MARGIN_RATIO = 0.3

FIELDS_COLOR = "#2f7d32"
SIGPAC_COLOR = "#d97706"
FILL_ALPHA = 64
OUTLINE_WIDTH_MM = 0.6
OUTLINE_HALO_COLOR = "#ffffff"
OUTLINE_HALO_ALPHA = 150
OUTLINE_HALO_WIDTH_MM = 1.2
LABEL_COLOR = "#0f172a"
LABEL_SIZE_PT = 10.0
LABEL_HALO_COLOR = "#ffffff"
LABEL_HALO_SIZE_MM = 1.0
LABEL_HALO_OPACITY = 0.85
LABEL_MAX_SCALE_DENOMINATOR = 50_000

SATELLITE_NAME = "Satellite (Esri World Imagery)"
SATELLITE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
SATELLITE_ATTRIBUTION = "Esri, Maxar, Earthstar Geographics"
SATELLITE_MAX_ZOOM = 19
BASEMAP_PROVIDERS = frozenset({"wms", "xyz", "arcgismapserver", "arcgisimageserver", "wcs", "mbtilesvectortiles"})
BASEMAP_LAYER_KINDS = frozenset({"raster", "vectortile"})


@dataclass(frozen=True)
class LayerInfo:
    kind: str
    provider: str


def is_basemap(layer: LayerInfo) -> bool:
    return layer.kind in BASEMAP_LAYER_KINDS or layer.provider.lower() in BASEMAP_PROVIDERS


def has_basemap(layers: Iterable[LayerInfo]) -> bool:
    return any(is_basemap(layer) for layer in layers)


def satellite_uri() -> str:
    url = SATELLITE_URL.replace("{", "%7B").replace("}", "%7D")
    return f"type=xyz&url={url}&zmin=0&zmax={SATELLITE_MAX_ZOOM}"


def format_area(area_ha: float | None) -> str:
    if area_ha is None:
        return ""
    if area_ha >= 1:
        return f"{area_ha:.{HECTARE_DECIMALS}f} ha"
    return f"{area_ha * SQUARE_METRES_PER_HECTARE:.0f} m²"


def label_expression(name_field: str, area_field: str) -> str:
    return (f'"{name_field}" || \'\\n\' || CASE WHEN "{area_field}" >= 1 '
            f'THEN format_number("{area_field}", {HECTARE_DECIMALS}) || \' ha\' '
            f'ELSE format_number("{area_field}" * {SQUARE_METRES_PER_HECTARE}, 0) || \' m²\' END')


def padded_extent(x_min: float, y_min: float, x_max: float, y_max: float,
                  minimum_half_size: float) -> tuple[float, float, float, float]:
    half_width = max((x_max - x_min) / 2 * (1 + ZOOM_MARGIN_RATIO), minimum_half_size)
    half_height = max((y_max - y_min) / 2 * (1 + ZOOM_MARGIN_RATIO), minimum_half_size)
    cx, cy = (x_min + x_max) / 2, (y_min + y_max) / 2
    return cx - half_width, cy - half_height, cx + half_width, cy + half_height


def rgba(color: str, alpha: int) -> str:
    color = color.lstrip("#")
    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    return f"{r},{g},{b},{alpha}"


def fill_properties(color: str) -> dict[str, str]:
    return {"color": rgba(color, FILL_ALPHA), "outline_style": "no", "style": "solid"}


def outline_properties(color: str) -> list[dict[str, str]]:
    return [
        {"line_color": rgba(OUTLINE_HALO_COLOR, OUTLINE_HALO_ALPHA), "line_width": str(OUTLINE_HALO_WIDTH_MM),
         "line_width_unit": "MM", "joinstyle": "round"},
        {"line_color": rgba(color, 255), "line_width": str(OUTLINE_WIDTH_MM), "line_width_unit": "MM",
         "joinstyle": "round"},
    ]
