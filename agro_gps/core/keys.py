from __future__ import annotations

AGRO_PREFIX = "agk_"
CATASTRO_PREFIXES = ("pk_live_", "pk_test_")
AGRO = "agro"
CATASTRO = "catastro"
UNKNOWN = "unknown"
EMPTY = "empty"


def key_kind(credential: str) -> str:
    value = (credential or "").strip()
    if not value:
        return EMPTY
    if value.startswith(AGRO_PREFIX):
        return AGRO
    if value.startswith(CATASTRO_PREFIXES):
        return CATASTRO
    return UNKNOWN
