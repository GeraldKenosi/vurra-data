import json
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"

PSL_TOURNAMENT_URL = "https://www.psl.co.za/tournament/betway-premiership"


def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])


def clean_name(value):
    return " ".join(value.replace("\xa0", " ").split())


def build_psl_recent_form_from_tournament_page():
    response = requests.get(PSL_TOURNAMENT_URL, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text_lines = [
        line.strip() for line in soup.get_text("\n").splitlines()
        if line.strip()
    ]

    team_results = {}
    team_ids = {}
    synthetic_id = 6000

    try:
        start_idx = text_lines.index("Match Centre")
    except ValueError:
        start_idx = 0

    i = start_idx
    while i < len(text_lines):
        if text_lines[i] == "Latest News":
            break

        if i + 3 < len(text_lines):
            home = clean_name(text_lines[i])
            score_line = text_lines[i + 1]
            away = clean_name(text_lines[i + 2])

            score_match = re.match(r"^(\d+)\s*-\s*(\d+)$", score_line)
            if score_match:
                home_goals = int(score_match.group(1))
                away_goals = int(score_match.group(2))

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
    for team_name, matches in team_results.items():
        if team_name not in team_ids:
            synthetic_id += 1
            team_ids[team_name] = synthetic_id

        normalized[str(team_ids[team_name])] = {
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
        output_file = PREDICTIONS_DIR / f"{league_key}_recent_form.json"

        if source == "football_data":
            print(f"Skipping API recent form for {league_key} to avoid 429 limits.")
            save_json({}, output_file)
            print(f"Saved empty recent form file: {output_file}")

        elif source == "psl_scraper":
            print("Building PSL recent form from tournament page results...")
            recent_form = build_psl_recent_form_from_tournament_page()
            save_json(recent_form, output_file)
            print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()