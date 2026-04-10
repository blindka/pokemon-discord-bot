"""
utils/battle_utils.py — חישובי קרב
"""
import random
import math


def calculate_damage(attacker: dict, defender: dict, move_name: str = None) -> int:
    """
    חישוב נזק — מבוסס על הנוסחה המקורית מהמשחק ה-React
    damage = max(floor(attack * 2 - defense * 0.7), 1)
    """
    attack = attacker.get("attack", 50)
    defense = defender.get("defense", 50)
    base_damage = max(math.floor(attack * 2 - defense * 0.7), 1)

    # ווריאציה אקראית ±15%
    variance = random.uniform(0.85, 1.15)
    damage = max(int(base_damage * variance), 1)
    return damage


def calculate_wild_damage(wild: dict, player_pokemon: dict) -> int:
    """נזק של פוקימון פראי על שחקן"""
    attack = wild.get("attack", 40)
    defense = player_pokemon.get("defense", 40)
    base_damage = max(math.floor(attack * 0.5 - defense * 0.1), 1)
    variance = random.uniform(0.85, 1.15)
    return max(int(base_damage * variance), 1)


def is_critical_hit(speed: int = 50) -> bool:
    """סיכוי לקריטי בהתאם למהירות"""
    crit_chance = min(speed / 512, 0.25)
    return random.random() < crit_chance


def get_move_info(move_name: str) -> dict:
    """מחזיר מידע על מהלך — כרגע מפושט"""
    MOVES = {
        "Vine Whip":     {"power": 45, "type": "Grass",    "emoji": "🌿"},
        "Razor Leaf":    {"power": 55, "type": "Grass",    "emoji": "🍃"},
        "Scratch":       {"power": 40, "type": "Normal",   "emoji": "✋"},
        "Ember":         {"power": 40, "type": "Fire",     "emoji": "🔥"},
        "Flamethrower":  {"power": 90, "type": "Fire",     "emoji": "🔥"},
        "Tackle":        {"power": 40, "type": "Normal",   "emoji": "💥"},
        "Water Gun":     {"power": 40, "type": "Water",    "emoji": "💧"},
        "Bubble":        {"power": 40, "type": "Water",    "emoji": "🫧"},
        "Thunder Shock": {"power": 40, "type": "Electric", "emoji": "⚡"},
        "Thunderbolt":   {"power": 90, "type": "Electric", "emoji": "⚡"},
        "Quick Attack":  {"power": 40, "type": "Normal",   "emoji": "💨"},
        "Bite":          {"power": 60, "type": "Dark",     "emoji": "🦷"},
        "Growl":         {"power": 0,  "type": "Normal",   "emoji": "😤", "status": True},
        "Leech Seed":    {"power": 0,  "type": "Grass",    "emoji": "🌱", "status": True},
        "Leech Life":    {"power": 80, "type": "Bug",      "emoji": "🐛"},
        "Poison Sting":  {"power": 15, "type": "Poison",  "emoji": "☠️"},
        "Solar Beam":    {"power": 120,"type": "Grass",    "emoji": "☀️"},
        "Hydro Pump":    {"power": 110,"type": "Water",    "emoji": "🌊"},
        "Hyper Beam":    {"power": 150,"type": "Normal",   "emoji": "🌟"},
        "Earthquake":    {"power": 100,"type": "Ground",   "emoji": "🌍"},
        "Psychic":       {"power": 90, "type": "Psychic",  "emoji": "🔮"},
        "Thunder":       {"power": 110,"type": "Electric", "emoji": "⛈️"},
        "Blizzard":      {"power": 110,"type": "Ice",      "emoji": "❄️"},
        "Wing Attack":   {"power": 60, "type": "Flying",   "emoji": "🦋"},
        "Slash":         {"power": 70, "type": "Normal",   "emoji": "⚔️"},
        "Fire Fang":     {"power": 65, "type": "Fire",     "emoji": "🔥"},
        "Skull Bash":    {"power": 130,"type": "Normal",   "emoji": "💀"},
        "Body Slam":     {"power": 85, "type": "Normal",   "emoji": "🤜"},
        "Double Kick":   {"power": 30, "type": "Fighting", "emoji": "🦶"},
        "Horn Attack":   {"power": 65, "type": "Normal",   "emoji": "🦏"},
        "Horn Drill":    {"power": 1,  "type": "Normal",   "emoji": "🔩"},
        "Sing":          {"power": 0,  "type": "Normal",   "emoji": "🎵", "status": True},
        "Confuse Ray":   {"power": 0,  "type": "Ghost",    "emoji": "😵", "status": True},
        "Sleep Powder":  {"power": 0,  "type": "Grass",    "emoji": "💤", "status": True},
        "Stun Spore":    {"power": 0,  "type": "Grass",    "emoji": "⚡", "status": True},
        "Poison Powder": {"power": 0,  "type": "Poison",   "emoji": "🟣", "status": True},
        "Wrap":          {"power": 15, "type": "Normal",   "emoji": "🔗"},
        "Sand Attack":   {"power": 0,  "type": "Ground",   "emoji": "🏜️", "status": True},
        "Agility":       {"power": 0,  "type": "Psychic",  "emoji": "💨", "status": True},
        "Tail Whip":     {"power": 0,  "type": "Normal",   "emoji": "🐾", "status": True},
        "Gust":          {"power": 40, "type": "Flying",   "emoji": "💨"},
        "Peck":          {"power": 35, "type": "Flying",   "emoji": "🐦"},
        "Fury Swipes":   {"power": 18, "type": "Normal",   "emoji": "💢"},
        "Mega Drain":    {"power": 40, "type": "Grass",    "emoji": "🌿"},
        "Absorb":        {"power": 20, "type": "Grass",    "emoji": "🌱"},
    }
    default = {"power": 40, "type": "Normal", "emoji": "💥"}
    return MOVES.get(move_name, default)


def format_battle_log(entries: list[str]) -> str:
    """מחזיר את 3 השורות האחרונות של יומן הקרב"""
    recent = entries[-3:] if len(entries) > 3 else entries
    return "\n".join(f"▸ {e}" for e in recent)
