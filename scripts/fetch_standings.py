import os
import json
import requests
from pathlib import Path

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")
}

PROJECT_DIR = Path(__file__).resolve().parent.parent
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"


def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])


def fetch_standings(league_id, season):
    url = f"{BASE_URL}/standings"
    params = {
        "league": league_id,
        "season": season
    }
    response = requests.get(url, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    ensure_folders()

    api_key = HEADERS.get("x-apisports-key")
    if not api_key:
        print("ERROR: API_FOOTBALL_KEY is missing.")
        return

    leagues = load_tracked_leagues()

    for league in leagues:
        league_id = league["league_id"]
        league_name = league["league_name"]
        season = league["season"]
        key = league["key"]

        print(f"Fetching standings for {league_name}...")
        data = fetch_standings(league_id, season)

        output_file = PREDICTIONS_DIR / f"{key}_standings.json"
        save_json(data, output_file)

        print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()