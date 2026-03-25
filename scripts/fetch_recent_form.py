import os
import json
import requests
from pathlib import Path

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")}
PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
LEAGUE_KEYS = ["premier_league", "bundesliga", "la_liga", "serie_a"]

def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def fetch_last_8_matches(team_id):
    response = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "last": 8}, timeout=30)
    response.raise_for_status()
    return response.json()

def collect_unique_teams(fixtures_data):
    teams = {}
    for fixture in fixtures_data.get("response", []):
        home = fixture.get("teams", {}).get("home", {})
        away = fixture.get("teams", {}).get("away", {})
        if home.get("id") and home.get("name"):
            teams[home["id"]] = home["name"]
        if away.get("id") and away.get("name"):
            teams[away["id"]] = away["name"]
    return teams

def main():
    ensure_folders()
    if not HEADERS["x-apisports-key"]:
        print("ERROR: API_FOOTBALL_KEY is missing.")
        return
    for league_key in LEAGUE_KEYS:
        fixtures_file = RESULTS_DIR / f"{league_key}_fixtures.json"
        if not fixtures_file.exists():
            continue
        fixtures_data = load_json(fixtures_file)
        unique_teams = collect_unique_teams(fixtures_data)
        league_recent_form = {}
        for team_id, team_name in unique_teams.items():
            recent_data = fetch_last_8_matches(team_id)
            league_recent_form[str(team_id)] = {"team_name": team_name, "matches": recent_data.get("response", [])}
        save_json(league_recent_form, PREDICTIONS_DIR / f"{league_key}_recent_form.json")
        print(f"Fetched recent form for {league_key}")

if __name__ == "__main__":
    main()
