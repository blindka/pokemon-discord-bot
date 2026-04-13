"""
config.py — הגדרות גלובליות של הבוט
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ===== BOT SETTINGS =====
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_TOKEN_HERE")
PREFIX = "!"
BOT_VERSION = "1.0.0"
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

# ===== GAME ECONOMY =====
STARTING_SILVER = 1000

# Silver reward per rarity tier when defeating a wild Pokémon
SILVER_REWARDS = {
    "common":    (1, 3),
    "uncommon":  (2, 5),
    "rare":      (3, 7),
    "very_rare": (5, 12),
    "legendary": (100, 500),
}

# ===== STORE PRICES =====
STORE_ITEMS = {
    "Poké Ball":    {"price": 200, "catch_rate": 1.0,  "type": "ball",   "emoji": "🔴"},
    "Great Ball":   {"price": 600, "catch_rate": 1.5,  "type": "ball",   "emoji": "🔵"},
    "Ultra Ball":   {"price": 1200,"catch_rate": 2.0,  "type": "ball",   "emoji": "⚫"},
    "Potion":       {"price": 300, "heal": 20,          "type": "potion", "emoji": "🧪"},
    "Super Potion": {"price": 700, "heal": 60,          "type": "potion", "emoji": "💊"},
    "Hyper Potion": {"price": 1500,"heal": 120,         "type": "potion", "emoji": "💉"},
}

STARTING_ITEMS = {"Poké Ball": 5}

# ===== BATTLE SETTINGS =====
BATTLE_TIMEOUT = 60       # שניות לתור
WILD_POKEMON_POOL = 151   # Gen 1 only

# ===== TYPE COLORS (for Discord Embeds) =====
TYPE_COLORS = {
    "Normal":   0xA8A878,
    "Fire":     0xF08030,
    "Water":    0x6890F0,
    "Electric": 0xF8D030,
    "Grass":    0x78C850,
    "Ice":      0x98D8D8,
    "Fighting": 0xC03028,
    "Poison":   0xA040A0,
    "Ground":   0xE0C068,
    "Flying":   0xA890F0,
    "Psychic":  0xF85888,
    "Bug":      0xA8B820,
    "Rock":     0xB8A038,
    "Ghost":    0x705898,
    "Dragon":   0x7038F8,
    "Dark":     0x705848,
    "Steel":    0xB8B8D0,
    "Fairy":    0xEE99AC,
}

TYPE_EMOJIS = {
    "Normal":   "⬜",
    "Fire":     "🔥",
    "Water":    "💧",
    "Electric": "⚡",
    "Grass":    "🌿",
    "Ice":      "❄️",
    "Fighting": "🥊",
    "Poison":   "☠️",
    "Ground":   "🌍",
    "Flying":   "🌪️",
    "Psychic":  "🔮",
    "Bug":      "🐛",
    "Rock":     "🪨",
    "Ghost":    "👻",
    "Dragon":   "🐉",
    "Dark":     "🌑",
    "Steel":    "⚙️",
    "Fairy":    "🧚",
}

# ===== STARTER POKEMON IDs =====
STARTER_IDS = [1, 4, 7]  # Bulbasaur, Charmander, Squirtle

# ===== NUMBER EMOJIS =====
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

# ===== DATABASE =====
DB_PATH = "data/pokemon_bot.db"

# ===== XP SYSTEM =====
XP_PER_BATTLE_WIN = 50      # XP בסיסי לניצחון בקרב
XP_LEVEL_BASE = 100         # XP הדרוש לרמה 1
XP_LEVEL_MULTIPLIER = 1.2   # כפול 1.2 לכל רמה עולה

# ===== EVOLUTION TABLE (pokemon_id: (evolves_to_id, min_level)) =====
EVOLUTION_TABLE = {
    1:  (2,  16),   # Bulbasaur   → Ivysaur
    2:  (3,  32),   # Ivysaur     → Venusaur
    4:  (5,  16),   # Charmander  → Charmeleon
    5:  (6,  36),   # Charmeleon  → Charizard
    7:  (8,  16),   # Squirtle    → Wartortle
    8:  (9,  36),   # Wartortle   → Blastoise
    10: (11, 7),    # Caterpie    → Metapod
    11: (12, 10),   # Metapod     → Butterfree
    13: (14, 7),    # Weedle      → Kakuna
    14: (15, 10),   # Kakuna      → Beedrill
    16: (17, 18),   # Pidgey      → Pidgeotto
    17: (18, 36),   # Pidgeotto   → Pidgeot
    19: (20, 20),   # Rattata     → Raticate
    21: (22, 20),   # Spearow     → Fearow
    23: (24, 22),   # Ekans       → Arbok
    25: (26, 22),   # Pikachu     → Raichu (Stone in game, here level)
    27: (28, 22),   # Sandshrew   → Sandslash
    29: (30, 16),   # Nidoran♀   → Nidorina
    30: (31, 36),   # Nidorina    → Nidoqueen
    32: (33, 16),   # Nidoran♂   → Nidorino
    33: (34, 36),   # Nidorino    → Nidoking
    37: (38, 29),   # Vulpix      → Ninetales
    39: (40, 18),   # Jigglypuff  → Wigglytuff
    41: (42, 22),   # Zubat       → Golbat
    43: (44, 21),   # Oddish      → Gloom
    44: (45, 36),   # Gloom       → Vileplume
    46: (47, 24),   # Paras       → Parasect
    48: (49, 31),   # Venonat     → Venomoth
    50: (51, 26),   # Diglett     → Dugtrio
    52: (53, 28),   # Meowth      → Persian
    54: (55, 33),   # Psyduck     → Golduck
    56: (57, 28),   # Mankey      → Primeape
    58: (59, 36),   # Growlithe   → Arcanine
    60: (61, 25),   # Poliwag     → Poliwhirl
    61: (62, 36),   # Poliwhirl   → Poliwrath
    63: (64, 16),   # Abra        → Kadabra
    64: (65, 36),   # Kadabra     → Alakazam
    66: (67, 28),   # Machop      → Machoke
    67: (68, 36),   # Machoke     → Machamp
    69: (70, 21),   # Bellsprout  → Weepinbell
    70: (71, 36),   # Weepinbell  → Victreebel
    72: (73, 30),   # Tentacool   → Tentacruel
    74: (75, 25),   # Geodude     → Graveler
    75: (76, 36),   # Graveler    → Golem
    77: (78, 40),   # Ponyta      → Rapidash
    79: (80, 37),   # Slowpoke    → Slowbro
    81: (82, 30),   # Magnemite   → Magneton
    84: (85, 28),   # Doduo       → Dodrio
    86: (87, 34),   # Seel        → Dewgong
    88: (89, 38),   # Grimer      → Muk
    90: (91, 30),   # Shellder    → Cloyster
    92: (94, 25),   # Gastly      → Haunter (skip Gengar for simplicity)
    95: (None, 0),  # Onix — no evolution (stone in original)
    96: (97, 26),   # Drowzee     → Hypno
    98: (99, 28),   # Krabby      → Kingler
    100:(101, 30),  # Voltorb     → Electrode
    102:(103, 36),  # Exeggcute   → Exeggutor
    104:(105, 28),  # Cubone      → Marowak
    109:(110, 35),  # Koffing     → Weezing
    111:(112, 42),  # Rhyhorn     → Rhydon
    116:(117, 25),  # Horsea      → Seadra
    118:(119, 33),  # Goldeen     → Seaking
    120:(121, 25),  # Staryu      → Starmie (Stone in original)
    129:(130, 20),  # Magikarp    → Gyarados
    133:(135, 25),  # Eevee       → Jolteon (simplified)
    138:(139, 40),  # Omanyte     → Omastar
    140:(141, 40),  # Kabuto      → Kabutops
}

# ===== ZONES (מפה אזורים) =====
ZONES = {
    "ocean": {
        "name": "🌊 ים",
        "emoji": "🌊",
        "pokemon": [54,55,60,61,62,72,73,79,80,86,87,90,91,
                    98,99,116,117,118,119,120,121,129,130,131,
                    134,138,139,140,141],
    },
    "forest": {
        "name": "🌿 יער",
        "emoji": "🌿",
        "pokemon": [1,2,3,10,11,12,13,14,15,43,44,45,46,47,
                    48,49,69,70,71,102,103,114],
    },
    "mountain": {
        "name": "⛰️ הרים",
        "emoji": "⛰️",
        "pokemon": [27,28,50,51,56,57,66,67,68,74,75,76,95,
                    111,112],
    },
    "city": {
        "name": "🏙️ עיר",
        "emoji": "🏙️",
        "pokemon": [19,20,25,26,35,36,39,40,52,53,63,64,65,
                    100,101,122,137],
    },
    "cave": {
        "name": "🕳️ מערה",
        "emoji": "🕳️",
        "pokemon": [41,42,74,75,92,93,94,96,97,109,110],
    },
    "grass": {
        "name": "🌾 שדה",
        "emoji": "🌾",
        "pokemon": [16,17,18,21,22,23,24,29,30,31,32,33,34,
                    37,38,58,59,77,78,83,84,85,128],
    },
}
DEFAULT_ZONE = "grass"
