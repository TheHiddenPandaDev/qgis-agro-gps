from __future__ import annotations

SPANISH = {
    "{n} farms.": "{n} explotaciones.",
    "{n} fields with an outline loaded.": "{n} parcelas con contorno cargadas.",
    "{ok} of {n} fields saved in your notebook.": "{ok} de {n} parcelas guardadas en tu cuaderno.",
    "Agro GPS - farm fields and SIGPAC": "Agro GPS - parcelas y SIGPAC",
    "Agro GPS key": "Clave de Agro GPS",
    "Agro GPS": "Agro GPS",
    "Click on a parcel on the map (Esc to cancel).": "Haz clic en una parcela del mapa (Esc para cancelar).",
    "Parcel lookup cancelled.": "Consulta de parcela cancelada.",
    "Country": "País",
    "Farm": "Explotación",
    "Field {id}": "Parcela {id}",
    "How to create a key": "Cómo crear una clave",
    "Key saved in your QGIS profile.": "Clave guardada en tu perfil de QGIS.",
    "Lat, lon": "Lat, lon",
    "Layer": "Capa",
    "Load farms": "Cargar explotaciones",
    "Load my fields as a layer": "Cargar mis parcelas como capa",
    "Load your farms and choose one first.": "Carga tus explotaciones y elige una primero.",
    "My fields": "Mis parcelas",
    "Name field": "Campo de nombre",
    "Paste the key from Agro GPS > Settings > API and webhooks":
        "Pega la clave de Agro GPS > Ajustes > API y webhooks",
    "Pick a point on the map": "Elegir un punto en el mapa",
    "Save key": "Guardar clave",
    "Search": "Buscar",
    "Choose a polygon layer first.": "Elige primero una capa de polígonos.",
    "No polygons selected in «{layer}». Select them with the Select Features tool, or pick a SIGPAC parcel, "
    "and try again.":
        "No hay polígonos seleccionados en «{layer}». Selecciónalos con la herramienta de selección, o elige una "
        "parcela SIGPAC, y vuelve a intentarlo.",
    "Send polygons to my notebook": "Enviar polígonos a mi cuaderno",
    "Send selected polygons": "Enviar polígonos seleccionados",
    "SIGPAC parcel (Spain)": "Parcela SIGPAC (España)",
    "SIGPAC returned a parcel without an outline.": "SIGPAC devolvió una parcela sin contorno.",
    "Type latitude and longitude as numbers.": "Escribe la latitud y la longitud como números.",
    "This key is from Catastro GPS. Create an Agro GPS key in Agro GPS > Settings > API and webhooks.":
        "Esta clave es de Catastro GPS; crea una de Agro GPS en Ajustes > API y webhooks.",
    "This does not look like an Agro GPS key (they start with agk_). Create one in Agro GPS > Settings > "
    "API and webhooks.":
        "Esta no parece una clave de Agro GPS (empiezan por agk_). Crea una en Agro GPS > Ajustes > API y webhooks.",
    "Your Agro GPS fields, SIGPAC parcels and sending polygons to your notebook":
        "Tus parcelas de Agro GPS, parcelas SIGPAC y envío de polígonos a tu cuaderno",
}

CATALOGUES = {"es": SPANISH, "ca": SPANISH, "gl": SPANISH, "eu": SPANISH}


def language_of(locale: str) -> str:
    return (locale or "").replace("-", "_").split("_")[0].lower()


def translate(text: str, locale: str) -> str:
    return CATALOGUES.get(language_of(locale), {}).get(text, text)
