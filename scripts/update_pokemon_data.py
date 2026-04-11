"""
scripts/update_pokemon_data.py
One-time script to enrich pokemon_data.json with real data from PokéAPI:
  - baseExp (base_experience) — used for XP calculation
  - catchRate (capture_rate) — original Gen-1 catch rate (0-255 scale)
  - Removes: expToNextLevel (unused field)
"""

import json
import urllib.request
import urllib.error
import time
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pokemon_data.json")
API_BASE  = "https://pokeapi.co/api/v2/pokemon/{id}"
SPECIES_BASE = "https://pokeapi.co/api/v2/pokemon-species/{id}"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def fetch_json(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Retry ({attempt+1}/{retries}) — {e}")
                time.sleep(1.5)
            else:
                raise


def main():
    print(f"Loading {DATA_PATH} ...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    pokemon_list = data["pokemon"]
    total = len(pokemon_list)

    for i, poke in enumerate(pokemon_list):
        pid = poke["id"]
        name = poke["name"]
        print(f"[{i+1}/{total}] #{pid} {name} ...", end=" ", flush=True)

        # --- base_experience from /pokemon endpoint ---
        try:
            p_data = fetch_json(API_BASE.format(id=pid))
            base_exp = p_data.get("base_experience") or 100
        except Exception as e:
            print(f"WARN: pokemon API failed ({e}), using default baseExp=100")
            base_exp = 100

        # --- capture_rate from /pokemon-species endpoint ---
        try:
            s_data = fetch_json(SPECIES_BASE.format(id=pid))
            catch_rate = s_data.get("capture_rate", 45)
        except Exception as e:
            print(f"WARN: species API failed ({e}), using default catchRate=45")
            catch_rate = 45

        # Update fields
        poke["baseExp"]   = base_exp
        poke["catchRate"] = catch_rate

        # Remove unused field
        poke.pop("expToNextLevel", None)

        print(f"baseExp={base_exp}, catchRate={catch_rate}")

        # Be polite to the API — avoid rate limiting
        time.sleep(0.3)

    print("\nWriting updated data ...")
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done! Updated {total} Pokémon entries.")


if __name__ == "__main__":
    main()
