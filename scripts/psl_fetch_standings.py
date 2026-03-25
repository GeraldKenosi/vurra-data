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


def scrape_psl_log(lines):
    rows = []
    synthetic_id = 5000

    i = 0
    while i + 4 < len(lines):
        a, b, c, d, e = lines[i], lines[i + 1], lines[i + 2], lines[i + 3], lines[i + 4]

        if (
            re.fullmatch(r"\d+", a)
            and not re.fullmatch(r"\d+", b)
            and re.fullmatch(r"\d+", c)
            and re.fullmatch(r"\d+", d)
            and re.fullmatch(r"\d+", e)
        ):
            rank = int(a)
            team_name = b
            played = int(c)
            wins = int(d)
            points = int(e)

            # Guard against false positives like goal scorers table
            if rank <= 20 and played <= 40 and wins <= 40 and points <= 120:
                synthetic_id += 1
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
                i += 5
                continue

        i += 1

    # Keep the most likely table by rank uniqueness and sort it
    seen = {}
    for row in rows:
        seen[row["rank"]] = row
    final_rows = [seen[k] for k in sorted(seen.keys()) if 1 <= k <= 16]

    return final_rows


def main():
    ensure_folders()

    print("Scraping PSL standings...")
    html = fetch_psl_page()
    lines = extract_lines(html)
    rows = scrape_psl_log(lines)

    output = {
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

    output_file = PREDICTIONS_DIR / "psl_standings.json"
    save_json(output, output_file)

    print(f"Saved: {output_file} | Rows: {len(rows)}")


if __name__ == "__main__":
    main()