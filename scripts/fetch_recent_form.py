import os
import json
import requests
from pathlib import Path

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")
}

PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"

LEAGUE_KEYS = [
    "premier_league",
    "bundesliga",
    "la_liga",
    "serie_a"
]


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
    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "last": 8
    }
    response = requests.get(url, headers=HEADERS, params=params, timeout=30)
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

    api_key = HEADERS.get("x-apisports-key")
    if not api_key:
        print("ERROR: API_FOOTBALL_KEY is missing.")
        return

    for league_key in LEAGUE_KEYS:
        fixtures_file = RESULTS_DIR / f"{league_key}_fixtures.json"

        if not fixtures_file.exists():
            print(f"Skipping {league_key} because fixtures file was not found.")
            continue

        fixtures_data = load_json(fixtures_file)
        unique_teams = collect_unique_teams(fixtures_data)

        league_recent_form = {}

        print(f"\nProcessing {league_key}...")
        print(f"Found {len(unique_teams)} unique teams in upcoming fixtures.")

        for team_id, team_name in unique_teams.items():
            print(f"Fetching last 8 matches for {team_name}...")
            recent_data = fetch_last_8_matches(team_id)

            league_recent_form[str(team_id)] = {
                "team_name": team_name,
                "matches": recent_data.get("response", [])
            }

        output_file = PREDICTIONS_DIR / f"{league_key}_recent_form.json"
        save_json(league_recent_form, output_file)

        print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()