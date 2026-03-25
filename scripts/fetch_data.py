import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LEAGUES_DIR = DATA_DIR / "leagues"

TRACKED_LEAGUES = [
    {
        "key": "premier_league",
        "league_name": "Premier League",
        "country": "England",
        "source": "football_data",
        "competition_code": "PL",
        "season": 2025
    },
    {
        "key": "bundesliga",
        "league_name": "Bundesliga",
        "country": "Germany",
        "source": "football_data",
        "competition_code": "BL1",
        "season": 2025
    },
    {
        "key": "la_liga",
        "league_name": "La Liga",
        "country": "Spain",
        "source": "football_data",
        "competition_code": "PD",
        "season": 2025
    },
    {
        "key": "serie_a",
        "league_name": "Serie A",
        "country": "Italy",
        "source": "football_data",
        "competition_code": "SA",
        "season": 2025
    },
    {
        "key": "psl",
        "league_name": "Betway Premiership",
        "country": "South Africa",
        "source": "psl_scraper",
        "competition_code": "PSL",
        "season": 2026
    }
]


def ensure_folders():
    LEAGUES_DIR.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    ensure_folders()

    output_file = LEAGUES_DIR / "tracked_leagues.json"
    save_json({"response": TRACKED_LEAGUES}, output_file)

    print(f"Saved tracked leagues to: {output_file}")
    for item in TRACKED_LEAGUES:
        print(
            f"{item['league_name']} | {item['country']} | "
            f"source={item['source']} | code={item['competition_code']}"
        )


if __name__ == "__main__":
    main()