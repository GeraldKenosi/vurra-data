import os
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"

FD_BASE_URL = "https://api.football-data.org/v4"
FD_HEADERS = {
    "X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY", "")
}

PSL_TOURNAMENT_URL = "https://www.psl.co.za/tournament/betway-premiership"


def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])


def fetch_fd_recent_matches(team_id):
    url = f"{FD_BASE_URL}/teams/{team_id}/matches"
    params = {"limit": 8}
    response = requests.get(url, headers=FD_HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_fd_recent_matches(raw):
    matches = raw.get("matches", [])
    normalized = []

    for item in matches:
        home = item.get("homeTeam", {})
        away = item.get("awayTeam", {})
        score = item.get("score", {})
        full_time = score.get("fullTime", {})

        normalized.append({
            "teams": {
                "home": {
                    "id": home.get("id"),
                    "name": home.get("name", "")
                },
                "away": {
                    "id": away.get("id"),
                    "name": away.get("name", "")
                }
            },
            "goals": {
                "home": full_time.get("home"),
                "away": full_time.get("away")
            }
        })

    return normalized


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


def build_psl_recent_form_from_results_page():
    response = requests.get(PSL_TOURNAMENT_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    text_lines = [
        line.strip() for line in soup.get_text("\n").splitlines()
        if line.strip()
    ]

    team_results = {}

    i = 0
    while i < len(text_lines) - 4:
        home = text_lines[i]
        score_line = text_lines[i + 1]
        away = text_lines[i + 2]

        if " - " in score_line:
            score_match = score_line.split(" - ")
            if len(score_match) == 2 and score_match[0].isdigit() and score_match[1].isdigit():
                home_goals = int(score_match[0])
                away_goals = int(score_match[1])

                match_obj = {
                    "teams": {
                        "home": {"id": None, "name": home},
                        "away": {"id": None, "name": away}
                    },
                    "goals": {
                        "home": home_goals,
                        "away": away_goals
                    }
                }

                team_results.setdefault(home, []).append(match_obj)
                team_results.setdefault(away, []).append(match_obj)

        i += 1

    normalized = {}
    for idx, (team_name, matches) in enumerate(team_results.items(), start=1):
        normalized[str(5000 + idx)] = {
            "team_name": team_name,
            "matches": matches[:8]
        }

    return normalized


def main():
    ensure_folders()

    leagues = load_tracked_leagues()

    for league in leagues:
        league_key = league["key"]
        source = league["source"]

        fixtures_file = RESULTS_DIR / f"{league_key}_fixtures.json"
        output_file = PREDICTIONS_DIR / f"{league_key}_recent_form.json"

        if source == "football_data":
            api_key = FD_HEADERS.get("X-Auth-Token")
            if not api_key:
                print("ERROR: FOOTBALL_DATA_API_KEY is missing.")
                return

            if not fixtures_file.exists():
                print(f"Skipping {league_key}: fixtures file missing.")
                continue

            fixtures_data = load_json(fixtures_file)
            unique_teams = collect_unique_teams(fixtures_data)
            recent_form = {}

            print(f"\nProcessing football-data recent form for {league_key}...")
            for team_id, team_name in unique_teams.items():
                print(f"Fetching last 8 matches for {team_name}...")
                raw = fetch_fd_recent_matches(team_id)
                recent_form[str(team_id)] = {
                    "team_name": team_name,
                    "matches": normalize_fd_recent_matches(raw)
                }

            save_json(recent_form, output_file)
            print(f"Saved: {output_file}")

        elif source == "psl_scraper":
            print("Building PSL recent form from results page...")
            recent_form = build_psl_recent_form_from_results_page()
            save_json(recent_form, output_file)
            print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()