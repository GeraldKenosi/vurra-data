import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")
}

PROJECT_DIR = Path(__file__).resolve().parent.parent
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"
RESULTS_DIR = PROJECT_DIR / "data" / "results"


def ensure_folders():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])


def fetch_upcoming_fixtures(league_id, season, date_from, date_to):
    url = f"{BASE_URL}/fixtures"
    params = {
        "league": league_id,
        "season": season,
        "from": date_from,
        "to": date_to,
        "status": "NS"
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

    today = datetime.now(timezone.utc).date()
    end_date = today + timedelta(days=7)

    date_from = today.isoformat()
    date_to = end_date.isoformat()

    print(f"Fetching upcoming fixtures from {date_from} to {date_to}...\n")

    for league in leagues:
        league_id = league["league_id"]
        league_name = league["league_name"]
        season = league["season"]
        key = league["key"]

        print(f"Fetching fixtures for {league_name}...")
        data = fetch_upcoming_fixtures(league_id, season, date_from, date_to)

        output_file = RESULTS_DIR / f"{key}_fixtures.json"
        save_json(data, output_file)

        print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()