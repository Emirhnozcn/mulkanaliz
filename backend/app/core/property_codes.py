"""Gayrimenkul türü kodları için takma adlar.

Veritabanı tohum verisi `residential_zoned_land` / `commercial_zoned_land` kodlarını kullanırken
arayüz ve eski analiz uçları `residential_land` / `commercial_land` gönderebilir. İki yazım da kabul edilir.
"""

_GROUPS = (
    ("residential_zoned_land", "residential_land"),
    ("commercial_zoned_land", "commercial_land"),
)

RESIDENTIAL_CODES = {"apartment", "detached_house", "villa"}
RESIDENTIAL_LAND_CODES = {"residential_zoned_land", "residential_land"}
LAND_CODES = {code for group in _GROUPS for code in group}


def code_aliases(code: str) -> list[str]:
    """Verilen kodun tüm eşdeğer yazımlarını döndürür."""
    for group in _GROUPS:
        if code in group:
            return list(group)
    return [code]
