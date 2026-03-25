import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).resolve().parent.parent
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"

FD_BASE_URL = "https://api.football-data.org/v4"
FD_HEADERS = {
    "X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY", "")
}

PSL_TOURNAMENT_URL = "https://www.psl.co.za/tournament/betway-premiership"


def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])


def fetch_fd_standings(code):
    url = f"{FD_BASE_URL}/competitions/{code}/standings"
    response = requests.get(url, headers=FD_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_fd_standings(raw, league_name, country):
    standings_blocks = raw.get("standings", [])
    if not standings_blocks:
        return {"response": []}

    table = standings_blocks[0].get("table", [])
    normalized_rows = []

    for row in table:
        team = row.get("team", {})
        normalized_rows.append({
            "rank": row.get("position", 999),
            "points": row.get("points", 0),
            "goalsDiff": row.get("goalDifference", 0),
            "form": "",
            "team": {
                "id": team.get("id"),
                "name": team.get("name", "")
            },
            "all": {
                "goals": {
                    "for": row.get("goalsFor", 0),
                    "against": row.get("goalsAgainst", 0),
                }
            }
        })

    return {
        "response": [
            {
                "league": {
                    "name": league_name,
                    "country": country,
                    "standings": [normalized_rows]
                }
            }
        ]
    }


def fetch_psl_page():
    response = requests.get(PSL_TOURNAMENT_URL, timeout=30)
    response.raise_for_status()
    return response.text


def clean_name(value):
    return " ".join(value.replace("\xa0", " ").split())


def scrape_psl_log(html):
    soup = BeautifulSoup(html, "html.parser")
    text_lines = [
        line.strip() for line in soup.get_text("\n").splitlines()
        if line.strip()
    ]

    try:
        start_idx = text_lines.index("Log")
    except ValueError:
        return {"response": []}

    rows = []
    i = start_idx + 1
    synthetic_id = 5001

    while i < len(text_lines):
        line = text_lines[i]

        if line.startswith("Videos") or line.startswith("Top Goal Scorers"):
            break

        team_match = re.match(r"^(\d+)\s+(.+)$", line)
        if team_match and i + 1 < len(text_lines):
            rank = int(team_match.group(1))
            team_name = clean_name(team_match.group(2))

            stats_line = text_lines[i + 1]
            stats_match = re.match(r"^(\d+)\s+(\d+)\s+(\d+)$", stats_line)

            if stats_match:
                played = int(stats_match.group(1))
                wins = int(stats_match.group(2))
                points = int(stats_match.group(3))

                rows.append({
                    "rank": rank,
                    "points": points,
                    "goalsDiff": max(0, wins - (played - wins)),
                    "form": "",
                    "team": {
                        "id": synthetic_id,
                        "name": team_name
                    },
                    "all": {
                        "goals": {
                            "for": wins,
                            "against": max(0, played - wins)
                        }
                    }
                })
                synthetic_id += 1
                i += 2
                continue

        i += 1

    return {
        "response": [
            {
                "league": {
                    "name": "Betway Premiership",
                    "country": "South Africa",
                    "standings": [rows]
                }
            }
        ]
    }


def main():
    ensure_folders()

    leagues = load_tracked_leagues()

    for league in leagues:
        key = league["key"]
        source = league["source"]
        league_name = league["league_name"]
        country = league["country"]

        output_file = PREDICTIONS_DIR / f"{key}_standings.json"

        if source == "football_data":
            api_key = FD_HEADERS.get("X-Auth-Token")
            if not api_key:
                print("ERROR: FOOTBALL_DATA_API_KEY is missing.")
                return

            code = league["competition_code"]
            print(f"Fetching football-data standings for {league_name}...")
            raw = fetch_fd_standings(code)
            normalized = normalize_fd_standings(raw, league_name, country)
            save_json(normalized, output_file)
            print(f"Saved: {output_file}")

        elif source == "psl_scraper":
            print("Scraping PSL log from tournament page...")
            html = fetch_psl_page()
            normalized = scrape_psl_log(html)
            save_json(normalized, output_file)
            print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()