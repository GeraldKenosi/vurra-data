import json
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"

PSL_TOURNAMENT_URL = "https://www.psl.co.za/tournament/betway-premiership"


def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def fetch_psl_page():
    response = requests.get(PSL_TOURNAMENT_URL, timeout=30)
    response.raise_for_status()
    return response.text


def extract_lines(html):
    soup = BeautifulSoup(html, "html.parser")
    return [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]


def build_recent_form(lines):
    team_results = {}
    team_ids = {}
    synthetic_id = 6000

    i = 0
    while i + 4 < len(lines):
        home = lines[i]
        score_line = lines[i + 1]
        away = lines[i + 2]
        match_summary = lines[i + 3]
        detail_line = lines[i + 4]

        score_match = re.match(r"^(\d+)\s*-\s*(\d+)$", score_line)

        if score_match and match_summary == "Match Summary":
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

            i += 5
            continue

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

    print("Scraping PSL recent results...")
    html = fetch_psl_page()
    lines = extract_lines(html)
    recent_form = build_recent_form(lines)

    output_file = PREDICTIONS_DIR / "psl_recent_form.json"
    save_json(recent_form, output_file)

    print(f"Saved: {output_file} | Teams: {len(recent_form)}")


if __name__ == "__main__":
    main()