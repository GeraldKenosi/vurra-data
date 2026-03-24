import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"

LEAGUE_FILES = [
    ("premier_league", "Premier League"),
    ("la_liga", "La Liga"),
    ("bundesliga", "Bundesliga"),
    ("serie_a", "Serie A"),
]


def load_json(filepath: Path):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def safe_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value))
    except Exception:
        return 0


def sort_key(item):
    confidence = safe_int(item.get("confidence", 0))
    date_str = str(item.get("date", ""))
    return (-confidence, date_str)


def main():
    combined = []
    by_league = {}

    for key_name, display_name in LEAGUE_FILES:
        file_path = PREDICTIONS_DIR / f"{key_name}_predictions.json"

        if not file_path.exists():
            print(f"Skipping {display_name}: file not found")
            by_league[key_name] = {
                "display_name": display_name,
                "count": 0,
            }
            continue

        data = load_json(file_path)
        response = data.get("response", [])

        cleaned = []
        for item in response:
            if not isinstance(item, dict):
                continue

            cleaned_item = dict(item)
            cleaned_item["league_key"] = key_name
            cleaned_item["league_display_name"] = display_name
            cleaned.append(cleaned_item)

        by_league[key_name] = {
            "display_name": display_name,
            "count": len(cleaned),
        }

        combined.extend(cleaned)

    combined.sort(key=sort_key)

    featured = combined[:12]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_matches": len(combined),
        "featured_count": len(featured),
        "by_league": by_league,
        "featured": featured,
        "response": combined,
    }

    output_file = PREDICTIONS_DIR / "home_summary.json"
    save_json(output, output_file)
    print(f"Saved: {output_file}")
    print(f"Total combined matches: {len(combined)}")
    print(f"Featured matches: {len(featured)}")


if __name__ == "__main__":
    main()