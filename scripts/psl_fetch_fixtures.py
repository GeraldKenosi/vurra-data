import json
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, UTC

PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "data" / "results"

PSL_TOURNAMENT_URL = "https://www.psl.co.za/tournament/betway-premiership"


def ensure_folders():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


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


def scrape_psl_fixtures(lines):
    fixtures = []
    fixture_id = 900000
    cutoff = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=45)

    i = 0
    while i + 3 < len(lines):
        home_team = lines[i]
        vs_line = lines[i + 1]
        away_team = lines[i + 2]
        detail_line = lines[i + 3]

        if vs_line == "VS":
            match = re.match(r"^(\d{2})\s+([A-Za-z]{3})\s+(\d{2}:\d{2})\s*-\s*(.+)$", detail_line)
            if match:
                day = match.group(1)
                month = match.group(2)
                time_part = match.group(3)
                venue = match.group(4).strip()

                try:
                    dt = datetime.strptime(
                        f"{day} {month} 2026 {time_part}",
                        "%d %b %Y %H:%M"
                    )
                    if dt <= cutoff:
                        iso_date = dt.strftime("%Y-%m-%dT%H:%M:00Z")

                        fixtures.append({
                            "fixture": {
                                "id": fixture_id,
                                "date": iso_date,
                                "venue": {
                                    "name": venue
                                },
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
                        i += 4
                        continue
                except ValueError:
                    pass

        i += 1

    return fixtures


def main():
    ensure_folders()

    print("Scraping PSL fixtures...")
    html = fetch_psl_page()
    lines = extract_lines(html)
    fixtures = scrape_psl_fixtures(lines)

    output = {"response": fixtures}
    output_file = RESULTS_DIR / "psl_fixtures.json"
    save_json(output, output_file)

    print(f"Saved: {output_file} | Rows: {len(fixtures)}")


if __name__ == "__main__":
    main()