import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")}
PROJECT_DIR = Path(__file__).resolve().parent.parent
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"
RESULTS_DIR = PROJECT_DIR / "data" / "results"

def ensure_folders():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])

def fetch_upcoming_fixtures(league_id, season, date_from, date_to):
    response = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"league": league_id, "season": season, "from": date_from, "to": date_to, "status": "NS"}, timeout=30)
    response.raise_for_status()
    return response.json()

def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main():
    ensure_folders()
    if not HEADERS["x-apisports-key"]:
        print("ERROR: API_FOOTBALL_KEY is missing.")
        return
    today = datetime.now(timezone.utc).date()
    end_date = today + timedelta(days=14)
    for league in load_tracked_leagues():
        data = fetch_upcoming_fixtures(league["league_id"], league["season"], today.isoformat(), end_date.isoformat())
        save_json(data, RESULTS_DIR / f'{league["key"]}_fixtures.json')
        print(f'Fetched fixtures for {league["league_name"]}')

if __name__ == "__main__":
    main()
