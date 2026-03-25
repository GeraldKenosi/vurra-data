import json
import re
from difflib import get_close_matches
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
RESULTS_DIR = PROJECT_DIR / "data" / "results"


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def normalize_team_key(name: str) -> str:
    if not name:
        return ""
    value = name.lower().strip()
    value = value.replace("&", "and")
    value = value.replace("-", " ")
    value = re.sub(r"\bfc\b", "", value)
    value = re.sub(r"\bfootball club\b", "", value)
    value = re.sub(r"\bclub\b", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9 ]", "", value)
    return value.strip()


def resolve_team_stats(team_name, team_lookup):
    key = normalize_team_key(team_name)

    if key in team_lookup:
        return team_lookup[key]

    close = get_close_matches(key, list(team_lookup.keys()), n=1, cutoff=0.70)
    if close:
        return team_lookup[close[0]]

    return None


def build_team_lookup(standings_data):
    lookup = {}

    response = standings_data.get("response", [])
    if not response:
        return lookup

    rows = response[0].get("league", {}).get("standings", [[]])[0]

    for row in rows:
        team = row.get("team", {})
        team_name = team.get("name", "")
        if not team_name:
            continue

        lookup[normalize_team_key(team_name)] = {
            "team_name": team_name,
            "rank": row.get("rank", 999),
            "points": row.get("points", 0),
            "goals_diff": row.get("goalsDiff", 0),
            "goals_for": row.get("all", {}).get("goals", {}).get("for", 0),
            "goals_against": row.get("all", {}).get("goals", {}).get("against", 0),
        }

    return lookup


def build_recent_form_lookup(recent_form_data):
    lookup = {}

    for value in recent_form_data.values():
        if not isinstance(value, dict):
            continue

        team_name = value.get("team_name", "")
        matches = value.get("matches", [])
        if team_name:
            lookup[normalize_team_key(team_name)] = matches

    return lookup


def weighted_recent_points(match_list, team_name):
    team_key = normalize_team_key(team_name)
    values = []

    for match in match_list:
        teams = match.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        goals = match.get("goals", {})

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        if normalize_team_key(home) == team_key:
            if home_goals > away_goals:
                values.append(3)
            elif home_goals == away_goals:
                values.append(1)
            else:
                values.append(0)
        elif normalize_team_key(away) == team_key:
            if away_goals > home_goals:
                values.append(3)
            elif away_goals == home_goals:
                values.append(1)
            else:
                values.append(0)

    if not values:
        return 0.5

    weights = list(range(len(values), 0, -1))
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    max_possible = sum(3 * w for w in weights)
    return weighted_sum / max_possible if max_possible else 0.5


def normalize_score(value, min_val, max_val):
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def calculate_strength(home, away, all_teams, recent_form_lookup):
    ranks = [t["rank"] for t in all_teams] or [1]
    points = [t["points"] for t in all_teams] or [0]
    gdiffs = [t["goals_diff"] for t in all_teams] or [0]
    goals_for = [t["goals_for"] for t in all_teams] or [0]

    home_rank_score = 1 - normalize_score(home["rank"], min(ranks), max(ranks))
    away_rank_score = 1 - normalize_score(away["rank"], min(ranks), max(ranks))

    home_points_score = normalize_score(home["points"], min(points), max(points))
    away_points_score = normalize_score(away["points"], min(points), max(points))

    home_gd_score = normalize_score(home["goals_diff"], min(gdiffs), max(gdiffs))
    away_gd_score = normalize_score(away["goals_diff"], min(gdiffs), max(gdiffs))

    home_goals_for_score = normalize_score(home["goals_for"], min(goals_for), max(goals_for))
    away_goals_for_score = normalize_score(away["goals_for"], min(goals_for), max(goals_for))

    home_recent = weighted_recent_points(
        recent_form_lookup.get(normalize_team_key(home["team_name"]), []),
        home["team_name"],
    )
    away_recent = weighted_recent_points(
        recent_form_lookup.get(normalize_team_key(away["team_name"]), []),
        away["team_name"],
    )

    home_total = (
        home_rank_score * 0.22 +
        home_points_score * 0.22 +
        home_gd_score * 0.14 +
        home_goals_for_score * 0.12 +
        home_recent * 0.25 +
        0.05
    )

    away_total = (
        away_rank_score * 0.22 +
        away_points_score * 0.22 +
        away_gd_score * 0.14 +
        away_goals_for_score * 0.12 +
        away_recent * 0.25
    )

    return {
        "home_strength": home_total,
        "away_strength": away_total,
        "home_recent": home_recent,
        "away_recent": away_recent,
    }


def main():
    standings_file = PREDICTIONS_DIR / "psl_standings.json"
    fixtures_file = RESULTS_DIR / "psl_fixtures.json"
    recent_form_file = PREDICTIONS_DIR / "psl_recent_form.json"
    output_file = PREDICTIONS_DIR / "psl_predictions.json"

    standings_data = load_json(standings_file)
    fixtures_data = load_json(fixtures_file)
    recent_form_data = load_json(recent_form_file)

    team_lookup = build_team_lookup(standings_data)
    recent_form_lookup = build_recent_form_lookup(recent_form_data)
    all_teams = list(team_lookup.values())

    predictions = []

    for fixture in fixtures_data.get("response", []):
        home_team = fixture.get("teams", {}).get("home", {}).get("name", "")
        away_team = fixture.get("teams", {}).get("away", {}).get("name", "")

        home_stats = resolve_team_stats(home_team, team_lookup)
        away_stats = resolve_team_stats(away_team, team_lookup)

        if not home_stats or not away_stats:
            print(f"Could not match PSL teams: {home_team} vs {away_team}")
            continue

        strength = calculate_strength(home_stats, away_stats, all_teams, recent_form_lookup)

        diff = strength["home_strength"] - strength["away_strength"]
        abs_diff = abs(diff)

        if abs_diff < 0.055:
            prediction = "Draw"
        elif diff > 0:
            prediction = "Home Win"
        else:
            prediction = "Away Win"

        confidence = min(88, max(53, round(52 + abs_diff * 100)))

        predictions.append({
            "fixture_id": fixture.get("fixture", {}).get("id"),
            "date": fixture.get("fixture", {}).get("date"),
            "league": "Betway Premiership",
            "country": "South Africa",
            "home_team": home_team,
            "away_team": away_team,
            "prediction": prediction,
            "confidence": confidence,
            "home_strength": round(strength["home_strength"], 3),
            "away_strength": round(strength["away_strength"], 3),
            "home_rank": home_stats["rank"],
            "away_rank": away_stats["rank"],
            "home_points": home_stats["points"],
            "away_points": away_stats["points"],
            "home_recent_overall": round(strength["home_recent"], 3),
            "away_recent_overall": round(strength["away_recent"], 3),
            "home_recent_home": round(strength["home_recent"], 3),
            "away_recent_away": round(strength["away_recent"], 3),
        })

    save_json({"response": predictions}, output_file)
    print(f"Saved: {output_file} | Count: {len(predictions)}")


if __name__ == "__main__":
    main()