import os
import json
import requests
from pathlib import Path

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")}

PROJECT_DIR = Path(__file__).resolve().parent.parent
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"

def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])

def fetch_standings(league_id, season):
    response = requests.get(f"{BASE_URL}/standings", headers=HEADERS, params={"league": league_id, "season": season}, timeout=30)
    response.raise_for_status()
    return response.json()

def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main():
    ensure_folders()
    if not HEADERS["x-apisports-key"]:
        print("ERROR: API_FOOTBALL_KEY is missing.")
        return
    for league in load_tracked_leagues():
        data = fetch_standings(league["league_id"], league["season"])
        save_json(data, PREDICTIONS_DIR / f'{league["key"]}_standings.json')
        print(f'Fetched standings for {league["league_name"]}')

if __name__ == "__main__":
    main()
