import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = PROJECT_DIR / "data" / "predictions"
RESULTS_DIR = PROJECT_DIR / "data" / "results"

def ensure_folders():
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def weighted_recent_points(match_list, team_id, venue=None):
    filtered = []
    for match in match_list:
        teams = match.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})
        goals = match.get("goals", {})
        is_home = home.get("id") == team_id
        is_away = away.get("id") == team_id
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
            points = 3 if home_goals > away_goals else 1 if home_goals == away_goals else 0
        else:
            points = 3 if away_goals > home_goals else 1 if away_goals == home_goals else 0
        filtered.append(points)
    if not filtered:
        return 0.0
    weights = list(range(len(filtered), 0, -1))
    weighted_sum = sum(p * w for p, w in zip(filtered, weights))
    max_possible = sum(3 * w for w in weights)
    return 0.0 if max_possible == 0 else weighted_sum / max_possible

def build_team_lookup(standings_data):
    lookup = {}
    response = standings_data.get("response", [])
    if not response:
        return lookup
    standings_groups = response[0].get("league", {}).get("standings", [])
    for group in standings_groups:
        for team_row in group:
            team = team_row.get("team", {})
            team_name = team.get("name")
            team_id = team.get("id")
            if not team_name or not team_id:
                continue
            goals = team_row.get("all", {}).get("goals", {})
            lookup[team_name.lower()] = {
                "team_id": team_id,
                "rank": team_row.get("rank", 999),
                "points": team_row.get("points", 0),
                "goals_diff": team_row.get("goalsDiff", 0),
                "goals_for": goals.get("for", 0),
                "goals_against": goals.get("against", 0),
                "team_name": team_name
            }
    return lookup

def normalize_score(value, min_val, max_val):
    return 0.5 if max_val == min_val else (value - min_val) / (max_val - min_val)

def calculate_strength(home, away, all_teams, recent_form_lookup):
    ranks = [t["rank"] for t in all_teams]
    points = [t["points"] for t in all_teams]
    gdiffs = [t["goals_diff"] for t in all_teams]
    goals_for = [t["goals_for"] for t in all_teams]
    home_rank_score = 1 - normalize_score(home["rank"], min(ranks), max(ranks))
    away_rank_score = 1 - normalize_score(away["rank"], min(ranks), max(ranks))
    home_points_score = normalize_score(home["points"], min(points), max(points))
    away_points_score = normalize_score(away["points"], min(points), max(points))
    home_gd_score = normalize_score(home["goals_diff"], min(gdiffs), max(gdiffs))
    away_gd_score = normalize_score(away["goals_diff"], min(gdiffs), max(gdiffs))
    home_goals_for_score = normalize_score(home["goals_for"], min(goals_for), max(goals_for))
    away_goals_for_score = normalize_score(away["goals_for"], min(goals_for), max(goals_for))
    home_recent_matches = recent_form_lookup.get(str(home["team_id"]), {}).get("matches", [])
    away_recent_matches = recent_form_lookup.get(str(away["team_id"]), {}).get("matches", [])
    home_recent_overall = weighted_recent_points(home_recent_matches, home["team_id"], venue=None)
    away_recent_overall = weighted_recent_points(away_recent_matches, away["team_id"], venue=None)
    home_recent_home = weighted_recent_points(home_recent_matches, home["team_id"], venue="home")
    away_recent_away = weighted_recent_points(away_recent_matches, away["team_id"], venue="away")
    home_total = home_rank_score*0.18 + home_points_score*0.18 + home_gd_score*0.14 + home_goals_for_score*0.10 + home_recent_overall*0.22 + home_recent_home*0.13 + 0.05
    away_total = away_rank_score*0.18 + away_points_score*0.18 + away_gd_score*0.14 + away_goals_for_score*0.10 + away_recent_overall*0.22 + away_recent_away*0.13
    return {"home_strength": home_total, "away_strength": away_total, "home_recent_overall": home_recent_overall, "away_recent_overall": away_recent_overall, "home_recent_home": home_recent_home, "away_recent_away": away_recent_away}

def build_prediction(home_team, away_team, home_stats, away_stats, all_teams, recent_form_lookup):
    strength = calculate_strength(home_stats, away_stats, all_teams, recent_form_lookup)
    diff = strength["home_strength"] - strength["away_strength"]
    abs_diff = abs(diff)
    prediction = "Draw" if abs_diff < 0.055 else "Home Win" if diff > 0 else "Away Win"
    confidence = min(88, max(53, round(52 + (abs_diff * 100))))
    return {
        "home_team": home_team, "away_team": away_team, "prediction": prediction, "confidence": confidence,
        "home_strength": round(strength["home_strength"], 3), "away_strength": round(strength["away_strength"], 3),
        "home_rank": home_stats["rank"], "away_rank": away_stats["rank"],
        "home_points": home_stats["points"], "away_points": away_stats["points"],
        "home_recent_overall": round(strength["home_recent_overall"], 3),
        "away_recent_overall": round(strength["away_recent_overall"], 3),
        "home_recent_home": round(strength["home_recent_home"], 3),
        "away_recent_away": round(strength["away_recent_away"], 3)
    }

def process_league(league_key):
    standings_data = load_json(PREDICTIONS_DIR / f"{league_key}_standings.json")
    fixtures_data = load_json(RESULTS_DIR / f"{league_key}_fixtures.json")
    recent_form_lookup = load_json(PREDICTIONS_DIR / f"{league_key}_recent_form.json")
    team_lookup = build_team_lookup(standings_data)
    all_teams = list(team_lookup.values())
    predictions = []
    for fixture in fixtures_data.get("response", []):
        teams = fixture.get("teams", {})
        home_team = teams.get("home", {}).get("name")
        away_team = teams.get("away", {}).get("name")
        if not home_team or not away_team:
            continue
        home_stats = team_lookup.get(home_team.lower())
        away_stats = team_lookup.get(away_team.lower())
        if not home_stats or not away_stats:
            continue
        prediction = build_prediction(home_team, away_team, home_stats, away_stats, all_teams, recent_form_lookup)
        predictions.append({
            "fixture_id": fixture.get("fixture", {}).get("id"),
            "date": fixture.get("fixture", {}).get("date"),
            "league": fixture.get("league", {}).get("name"),
            "country": fixture.get("league", {}).get("country"),
            **prediction
        })
    save_json({"response": predictions}, PREDICTIONS_DIR / f"{league_key}_predictions.json")

def main():
    ensure_folders()
    for league_key in ["premier_league", "bundesliga", "la_liga", "serie_a"]:
        process_league(league_key)

if __name__ == "__main__":
    main()
