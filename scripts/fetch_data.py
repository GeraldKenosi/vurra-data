import os
import json
from pathlib import Path

BASE_URL = "https://v3.football.api-sports.io"

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LEAGUES_DIR = DATA_DIR / "leagues"

CONFIRMED_LEAGUES = [
    {
        "key": "premier_league",
        "league_id": 39,
        "league_name": "Premier League",
        "country": "England",
        "season": 2025
    },
    {
        "key": "bundesliga",
        "league_id": 78,
        "league_name": "Bundesliga",
        "country": "Germany",
        "season": 2025
    },
    {
        "key": "la_liga",
        "league_id": 140,
        "league_name": "La Liga",
        "country": "Spain",
        "season": 2025
    },
    {
        "key": "serie_a",
        "league_id": 135,
        "league_name": "Serie A",
        "country": "Italy",
        "season": 2025
    }
]


def ensure_folders():
    LEAGUES_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    ensure_folders()

    api_key = os.getenv("API_FOOTBALL_KEY", "")
    if not api_key:
        print("ERROR: API_FOOTBALL_KEY is missing.")
        return

    output_file = LEAGUES_DIR / "tracked_leagues.json"
    save_json({"response": CONFIRMED_LEAGUES}, output_file)

    print(f"Saved confirmed leagues to: {output_file}")
    print("\nTracked leagues:\n")

    for item in CONFIRMED_LEAGUES:
        print(
            f"{item['country']} | {item['league_name']} | "
            f"ID: {item['league_id']} | Season: {item['season']}"
        )


if __name__ == "__main__":
    main()