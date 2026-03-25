import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
LEAGUE_FILES = [("premier_league", "Premier League"), ("la_liga", "La Liga"), ("bundesliga", "Bundesliga"), ("serie_a", "Serie A")]

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, filepath):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0

def sort_key(item):
    return (-safe_int(item.get("confidence", 0)), str(item.get("date", "")))

def main():
    combined = []
    by_league = {}
    for key_name, display_name in LEAGUE_FILES:
        file_path = PREDICTIONS_DIR / f"{key_name}_predictions.json"
        if not file_path.exists():
            by_league[key_name] = {"display_name": display_name, "count": 0}
            continue
        response = load_json(file_path).get("response", [])
        cleaned = []
        for item in response:
            if isinstance(item, dict):
                row = dict(item)
                row["league_key"] = key_name
                row["league_display_name"] = display_name
                cleaned.append(row)
        by_league[key_name] = {"display_name": display_name, "count": len(cleaned)}
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
    save_json(output, PREDICTIONS_DIR / "home_summary.json")

if __name__ == "__main__":
    main()
