"""
utils/pokemon_utils.py — פונקציות עזר לנתוני פוקימונים
"""
import json
import random
from typing import Optional, List
import os

# טעינת נתוני פוקימון מהקובץ
_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pokemon_data.json")
with open(_DATA_PATH, "r", encoding="utf-8") as f:
    _ALL_POKEMON = json.load(f)["pokemon"]

# מיפוי ID -> נתונים
_POKEMON_BY_ID = {p["id"]: p for p in _ALL_POKEMON}
_POKEMON_BY_NAME = {p["name"].lower(): p for p in _ALL_POKEMON}

# ===== RARITY SYSTEM =====
# Encounter rates use a 1-in-N probability model.
# The weight stored is 1/N so that random.choices works correctly.

# Legendary / Mythical — 1 in 2048
_LEGENDARY_IDS = {144, 145, 146, 150, 151}  # Articuno, Zapdos, Moltres, Mewtwo, Mew

# Very Rare — 1 in 256 (starter families, normally unobtainable in the wild)
_VERY_RARE_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9}

# Rare — 1 in 32 (strong evolved / special Pokémon)
_RARE_IDS = {
    130, 131, 143,       # Gyarados, Lapras, Snorlax
    149, 142, 139,       # Dragonite, Aerodactyl, Omastar
    141, 134, 135, 136,  # Kabutops, Vaporeon, Jolteon, Flareon
    65, 68, 76, 94,      # Alakazam, Machamp, Golem, Gengar
    103, 112, 115,       # Exeggutor, Rhydon, Kangaskhan
}

# 1-in-N encounter probabilities
_ENCOUNTER_RATES = {
    "legendary": 1 / 2048,
    "very_rare":  1 / 256,
    "rare":       1 / 32,
    "uncommon":   1 / 16,
    "common":     1 / 8,
}


def get_rarity(pokemon_id: int) -> str:
    """מחזיר רמת נדירות: common, uncommon, rare, very_rare, legendary"""
    if pokemon_id in _LEGENDARY_IDS:
        return "legendary"
    if pokemon_id in _VERY_RARE_IDS:
        return "very_rare"
    if pokemon_id in _RARE_IDS:
        return "rare"
    poke = _POKEMON_BY_ID.get(pokemon_id)
    if poke:
        power = poke.get("power", 300)
        if power >= 450:
            return "rare"
        elif power >= 380:
            return "uncommon"
    return "common"


def get_rarity_emoji(pokemon_id: int) -> str:
    r = get_rarity(pokemon_id)
    return {
        "common":    "⚪",
        "uncommon":  "🟢",
        "rare":      "🔵",
        "very_rare": "🟣",
        "legendary": "🟡",
    }[r]


def _weighted_pick(pokemon_ids: list) -> int:
    """בוחר פוקימון לפי שיטת 1-in-N encounter rates"""
    weighted = []
    weights = []
    for pid in pokemon_ids:
        r = get_rarity(pid)
        weighted.append(pid)
        weights.append(_ENCOUNTER_RATES.get(r, 1 / 8))

    if not weighted:
        return random.choice(pokemon_ids)
    return random.choices(weighted, weights=weights, k=1)[0]


def get_pokemon_by_id(pokemon_id: int) -> Optional[dict]:
    return _POKEMON_BY_ID.get(pokemon_id)


def get_pokemon_by_name(name: str) -> Optional[dict]:
    return _POKEMON_BY_NAME.get(name.lower())


def get_all_pokemon() -> List[dict]:
    return _ALL_POKEMON


def get_random_wild_pokemon(max_id: int = 151) -> Optional[dict]:
    """מחזיר פוקימון פראי אקראי עם HP מלא, רמה 5-10"""
    pool = [p["id"] for p in _ALL_POKEMON if p["id"] <= max_id]
    pid = _weighted_pick(pool)
    chosen = _POKEMON_BY_ID.get(pid) or random.choice(_ALL_POKEMON)
    return {
        **chosen,
        "current_hp": chosen["hp"],
        "max_hp": chosen["hp"],
        "level": random.randint(5, 10),
    }


def get_wild_pokemon_for_zone(zone: str, player_level: int = 5) -> Optional[dict]:
    """
    מחזיר פוקימון פראי בהתאם לאזור:
    70% מהאזור הספציפי, 30% כל Gen 1
    רמה: 5-10 קבוע (ללא קשר לרמת השחקן)
    משתמש במערכת נדירות 1-in-N
    """
    from config import ZONES, DEFAULT_ZONE
    zone_data = ZONES.get(zone, ZONES.get(DEFAULT_ZONE))
    zone_ids = zone_data["pokemon"]

    available_ids = [p["id"] for p in _ALL_POKEMON if p["id"] <= 151]
    zone_valid = [pid for pid in zone_ids if pid in available_ids]

    if zone_valid and random.random() < 0.70:
        pid = _weighted_pick(zone_valid)
    else:
        pid = _weighted_pick(available_ids)

    chosen = _POKEMON_BY_ID.get(pid) or random.choice(_ALL_POKEMON)

    return {
        **chosen,
        "current_hp": chosen["hp"],
        "max_hp": chosen["hp"],
        "level": random.randint(5, 10),
    }




def get_sprite_url(pokemon_id: int) -> str:
    """מחזיר URL של sprite מה-PokeAPI"""
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pokemon_id}.png"


def get_animated_sprite_url(pokemon_id: int) -> str:
    """מחזיר animated gif sprite"""
    return (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master/"
        f"sprites/pokemon/versions/generation-v/black-white/animated/{pokemon_id}.gif"
    )


def build_hp_bar(current: int, maximum: int, length: int = 10) -> str:
    """מייצר פס HP גרפי"""
    if maximum == 0:
        return "░" * length
    filled = round((current / maximum) * length)
    filled = max(0, min(filled, length))
    bar = "█" * filled + "░" * (length - filled)
    pct = (current / maximum) * 100
    if pct > 50:
        color = "🟢"
    elif pct > 20:
        color = "🟡"
    else:
        color = "🔴"
    return f"{color} `{bar}` {current}/{maximum}"


def get_type_emoji(pokemon_type: str) -> str:
    from config import TYPE_EMOJIS
    return TYPE_EMOJIS.get(pokemon_type, "❓")


def get_primary_color(pokemon: dict) -> int:
    from config import TYPE_COLORS
    types = pokemon.get("type", ["Normal"])
    return TYPE_COLORS.get(types[0], 0xA8A878)


def format_pokemon_types(types: list) -> str:
    from config import TYPE_EMOJIS
    return " / ".join(f"{TYPE_EMOJIS.get(t, '')} {t}" for t in types)


def calculate_catch_rate(wild_pokemon: dict, ball_multiplier: float = 1.0) -> float:
    """
    חישוב סיכוי תפיסה — בהתחשב ב-HP נותר וסוג הכדור
    """
    hp_ratio = wild_pokemon["current_hp"] / wild_pokemon["max_hp"]
    base_rate = 0.35  # 35% base
    hp_bonus = (1 - hp_ratio) * 0.35  # עד 35% בונוס כש-HP נמוך
    catch_chance = (base_rate + hp_bonus) * ball_multiplier
    return min(catch_chance, 0.95)  # cap at 95%


def get_starters() -> List[Optional[dict]]:
    """מחזיר את 3 הפוקימונים ההתחלתיים"""
    from config import STARTER_IDS
    return [get_pokemon_by_id(pid) for pid in STARTER_IDS]
