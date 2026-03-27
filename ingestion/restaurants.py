"""Restaurant name/id mapping used by ingestion workflows."""

RESTAURANT_NAME_MAP = {
    "Mozza EmQuartier": "mozza-emq",
    "Mozza Emquartier": "mozza-emq",
    "Cocotte": "cocotte-39",
    "Mozza Paragon": "mozza-prg",
    "Mozza Icon Siam": "mozza-icsm",
    "Mozza IconSiam": "mozza-icsm",
    "Mozza Central Park": "mozza-cp",
    "Parma Eastville": "parma-eastville",
    "Parma Central Eastville": "parma-eastville",
}

ID_TO_CANONICAL_NAME = {}
for _name, _rid in RESTAURANT_NAME_MAP.items():
    if _rid not in ID_TO_CANONICAL_NAME:
        ID_TO_CANONICAL_NAME[_rid] = _name

