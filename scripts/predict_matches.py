import json
import re
from difflib import get_close_matches
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
RESULTS_DIR = PROJECT_DIR / "data" / "results"
LEAGUES_FILE = PROJECT_DIR / "data" / "leagues" / "tracked_leagues.json"


def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)


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
    value = value.replace("_", " ")
    value = re.sub(r"\bfc\b", "", value)
    value = re.sub(r"\bfootball club\b", "", value)
    value = re.sub(r"\bclub\b", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9 ]", "", value)
    return value.strip()


def resolve_team_stats(team_name, team_lookup):
    normalized = normalize_team_key(team_name)

    if normalized in team_lookup:
        return team_lookup[normalized]

    all_keys = list(team_lookup.keys())
    close = get_close_matches(normalized, all_keys, n=1, cutoff=0.72)

    if close:
        return team_lookup[close[0]]

    return None


def weighted_recent_points(match_list, team_name, venue=None):
    filtered = []
    team_key = normalize_team_key(team_name)

    for match in match_list:
        teams = match.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})
        goals = match.get("goals", {})

        home_name = home.get("name", "")
        away_name = away.get("name", "")

        is_home = normalize_team_key(home_name) == team_key
        is_away = normalize_team_key(away_name) == team_key

        if venue == "home" and not is_home:
            continue
        if venue == "away" and not is_away:
            continue
        if not (is_home or is_away):
            continue

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        if is_home:
            if home_goals > away_goals:
                points = 3
            elif home_goals == away_goals:
                points = 1
            else:
                points = 0
        else:
            if away_goals > home_goals:
                points = 3
            elif away_goals == home_goals:
                points = 1
            else:
                points = 0

        filtered.append(points)

    if not filtered:
        return 0.0

    weights = list(range(len(filtered), 0, -1))
    weighted_sum = sum(p * w for p, w in zip(filtered, weights))
    max_possible = sum(3 * w for w in weights)

    if max_possible == 0:
        return 0.0

    return weighted_sum / max_possible


def build_team_lookup(standings_data):
    lookup = {}

    response = standings_data.get("response", [])
    if not response:
        return lookup

    league_block = response[0]
    league_info = league_block.get("league", {})
    standings_groups = league_info.get("standings", [])

    for group in standings_groups:
        for team_row in group:
            team = team_row.get("team", {})
            team_name = team.get("name")

            if not team_name:
                continue

            all_stats = team_row.get("all", {})
            goals = all_stats.get("goals", {})

            lookup[normalize_team_key(team_name)] = {
                "team_id": team.get("id"),
                "rank": team_row.get("rank", 999),
                "points": team_row.get("points", 0),
                "goals_diff": team_row.get("goalsDiff", 0),
                "goals_for": goals.get("for", 0),
                "goals_against": goals.get("against", 0),
                "team_name": team_name
            }

    return lookup


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

    home_recent_matches = recent_form_lookup.get(normalize_team_key(home["team_name"]), [])
    away_recent_matches = recent_form_lookup.get(normalize_team_key(away["team_name"]), [])

    home_recent_overall = weighted_recent_points(home_recent_matches, home["team_name"], venue=None)
    away_recent_overall = weighted_recent_points(away_recent_matches, away["team_name"], venue=None)

    home_recent_home = weighted_recent_points(home_recent_matches, home["team_name"], venue="home")
    away_recent_away = weighted_recent_points(away_recent_matches, away["team_name"], venue="away")

    home_total = (
        home_rank_score * 0.18 +
        home_points_score * 0.18 +
        home_gd_score * 0.14 +
        home_goals_for_score * 0.10 +
        home_recent_overall * 0.22 +
        home_recent_home * 0.13 +
        0.05
    )

    away_total = (
        away_rank_score * 0.18 +
        away_points_score * 0.18 +
        away_gd_score * 0.14 +
        away_goals_for_score * 0.10 +
        away_recent_overall * 0.22 +
        away_recent_away * 0.13
    )

    return {
        "home_strength": home_total,
        "away_strength": away_total,
        "home_recent_overall": home_recent_overall,
        "away_recent_overall": away_recent_overall,
        "home_recent_home": home_recent_home,
        "away_recent_away": away_recent_away,
    }


def build_prediction(home_team, away_team, home_stats, away_stats, all_teams, recent_form_lookup):
    strength = calculate_strength(home_stats, away_stats, all_teams, recent_form_lookup)

    home_strength = strength["home_strength"]
    away_strength = strength["away_strength"]

    diff = home_strength - away_strength
    abs_diff = abs(diff)

    if abs_diff < 0.055:
        prediction = "Draw"
    elif diff > 0:
        prediction = "Home Win"
    else:
        prediction = "Away Win"

    confidence = min(88, max(53, round(52 + (abs_diff * 100))))

    return {
        "home_team": home_team,
        "away_team": away_team,
        "prediction": prediction,
        "confidence": confidence,
        "home_strength": round(home_strength, 3),
        "away_strength": round(away_strength, 3),
        "home_rank": home_stats["rank"],
        "away_rank": away_stats["rank"],
        "home_points": home_stats["points"],
        "away_points": away_stats["points"],
        "home_recent_overall": round(strength["home_recent_overall"], 3),
        "away_recent_overall": round(strength["away_recent_overall"], 3),
        "home_recent_home": round(strength["home_recent_home"], 3),
        "away_recent_away": round(strength["away_recent_away"], 3)
    }


def build_recent_form_lookup(recent_form_data):
    lookup = {}

    if isinstance(recent_form_data, dict):
        for value in recent_form_data.values():
            if not isinstance(value, dict):
                continue
            team_name = value.get("team_name", "")
            matches = value.get("matches", [])
            if team_name:
                lookup[normalize_team_key(team_name)] = matches

    return lookup


def process_league(league_key):
    standings_file = PREDICTIONS_DIR / f"{league_key}_standings.json"
    fixtures_file = RESULTS_DIR / f"{league_key}_fixtures.json"
    recent_form_file = PREDICTIONS_DIR / f"{league_key}_recent_form.json"
    output_file = PREDICTIONS_DIR / f"{league_key}_predictions.json"

    if not standings_file.exists() or not fixtures_file.exists():
        save_json({"response": []}, output_file)
        print(f"Skipped {league_key}: missing standings or fixtures.")
        return

    standings_data = load_json(standings_file)
    fixtures_data = load_json(fixtures_file)

    recent_form_data = {}
    if recent_form_file.exists():
        recent_form_data = load_json(recent_form_file)

    recent_form_lookup = build_recent_form_lookup(recent_form_data)
    team_lookup = build_team_lookup(standings_data)
    all_teams = list(team_lookup.values())

    predictions = []

    for fixture in fixtures_data.get("response", []):
        teams = fixture.get("teams", {})
        home_team = teams.get("home", {}).get("name")
        away_team = teams.get("away", {}).get("name")

        if not home_team or not away_team:
            continue

        home_stats = resolve_team_stats(home_team, team_lookup)
        away_stats = resolve_team_stats(away_team, team_lookup)

        if not home_stats or not away_stats:
            print(f"Could not match teams for {league_key}: {home_team} vs {away_team}")
            continue

        prediction = build_prediction(
            home_team,
            away_team,
            home_stats,
            away_stats,
            all_teams,
            recent_form_lookup
        )

        predictions.append({
            "fixture_id": fixture.get("fixture", {}).get("id"),
            "date": fixture.get("fixture", {}).get("date"),
            "league": fixture.get("league", {}).get("name"),
            "country": fixture.get("league", {}).get("country"),
            **prediction
        })

    save_json({"response": predictions}, output_file)
    print(f"Saved predictions: {output_file} | Count: {len(predictions)}")


def main():
    ensure_folders()

    leagues_data = load_json(LEAGUES_FILE).get("response", [])
    league_keys = [league["key"] for league in leagues_data]

    for league_key in league_keys:
        print(f"Processing {league_key}...")
        process_league(league_key)


if __name__ == "__main__":
    main()