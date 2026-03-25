import os
import re
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).resolve().parent.parent
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"
RESULTS_DIR = PROJECT_DIR / "data" / "results"

FD_BASE_URL = "https://api.football-data.org/v4"
FD_HEADERS = {
    "X-Auth-Token": os.getenv("FOOTBALL_DATA_API_KEY", "")
}

PSL_MATCH_CENTRE_URL = "https://www.psl.co.za/matchcentre"


def ensure_folders():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_tracked_leagues():
    with open(LEAGUES_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("response", [])


def fetch_fd_matches(code, date_from, date_to):
    url = f"{FD_BASE_URL}/competitions/{code}/matches"
    params = {
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    response = requests.get(url, headers=FD_HEADERS, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_fd_matches(raw, league_name, country):
    matches = raw.get("matches", [])
    normalized = []

    for item in matches:
        status = item.get("status", "")
        if status not in {"SCHEDULED", "TIMED", "POSTPONED"}:
            continue

        home = item.get("homeTeam", {})
        away = item.get("awayTeam", {})

        normalized.append({
            "fixture": {
                "id": item.get("id"),
                "date": item.get("utcDate"),
                "status": {
                    "short": "NS"
                }
            },
            "league": {
                "name": league_name,
                "country": country
            },
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
                "home": None,
                "away": None
            }
        })

    normalized.sort(key=lambda x: x["fixture"]["date"] or "")
    return {"response": normalized}


def fetch_psl_page():
    response = requests.get(PSL_MATCH_CENTRE_URL, timeout=30)
    response.raise_for_status()
    return response.text


def parse_psl_date(date_str):
    year = 2026
    return datetime.strptime(f"{date_str} {year}", "%d %b %Y")


def normalize_team_name(name):
    return " ".join(name.replace("\xa0", " ").split())


def scrape_psl_upcoming_fixtures(html):
    soup = BeautifulSoup(html, "lxml")
    text_lines = [
        line.strip() for line in soup.get_text("\n").splitlines()
        if line.strip()
    ]

    fixtures = []
    current_date = None
    i = 0
    fixture_id = 900000

    cutoff = datetime.utcnow() + timedelta(days=21)

    while i < len(text_lines):
        line = text_lines[i]

        if re.match(r"^\d{2}\s+[A-Za-z]{3}\s+\d{4}$", line):
            current_date = line
            i += 1
            continue

        if (
            current_date
            and i + 3 < len(text_lines)
            and text_lines[i + 1] == "VS"
        ):
            home_team = normalize_team_name(text_lines[i])
            away_team = normalize_team_name(text_lines[i + 2])
            detail_line = text_lines[i + 3]

            if re.match(r"^\d{2}\s+[A-Za-z]{3}\s+\d{2}:\d{2}", f"{current_date}"):
                try:
                    match_date = parse_psl_date(current_date)
                    if match_date <= cutoff:
                        time_match = re.match(r"^(\d{2}\s+[A-Za-z]{3}\s+\d{2}:\d{2})\s*-\s*(.*)$", f"{current_date.split()[0]} {current_date.split()[1]} {detail_line}")
                except Exception:
                    pass

            try:
                dt = parse_psl_date(current_date)
                if dt <= cutoff:
                    date_part = dt.strftime("%Y-%m-%d")
                    time_part = detail_line.split(" - ")[0].strip() if " - " in detail_line else "15:00"
                    iso_date = f"{date_part}T{time_part}:00Z"

                    fixtures.append({
                        "fixture": {
                            "id": fixture_id,
                            "date": iso_date,
                            "status": {
                                "short": "NS"
                            }
                        },
                        "league": {
                            "name": "Betway Premiership",
                            "country": "South Africa"
                        },
                        "teams": {
                            "home": {
                                "id": None,
                                "name": home_team
                            },
                            "away": {
                                "id": None,
                                "name": away_team
                            }
                        },
                        "goals": {
                            "home": None,
                            "away": None
                        }
                    })
                    fixture_id += 1
            except Exception:
                pass

            i += 4
            continue

        i += 1

    return {"response": fixtures}


def main():
    ensure_folders()

    leagues = load_tracked_leagues()

    today = datetime.utcnow().date()
    date_from = today.isoformat()
    date_to = (today + timedelta(days=21)).isoformat()

    print(f"Fetching fixtures from {date_from} to {date_to}...\n")

    for league in leagues:
        key = league["key"]
        source = league["source"]
        league_name = league["league_name"]
        country = league["country"]
        output_file = RESULTS_DIR / f"{key}_fixtures.json"

        if source == "football_data":
            api_key = FD_HEADERS.get("X-Auth-Token")
            if not api_key:
                print("ERROR: FOOTBALL_DATA_API_KEY is missing.")
                return

            code = league["competition_code"]
            print(f"Fetching football-data fixtures for {league_name}...")
            raw = fetch_fd_matches(code, date_from, date_to)
            normalized = normalize_fd_matches(raw, league_name, country)
            save_json(normalized, output_file)
            print(f"Saved: {output_file} | Count: {len(normalized.get('response', []))}")

        elif source == "psl_scraper":
            print("Scraping PSL fixtures...")
            html = fetch_psl_page()
            normalized = scrape_psl_upcoming_fixtures(html)
            save_json(normalized, output_file)
            print(f"Saved: {output_file} | Count: {len(normalized.get('response', []))}")


if __name__ == "__main__":
    main()