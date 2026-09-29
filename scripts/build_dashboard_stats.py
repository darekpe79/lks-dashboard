import json
from datetime import datetime, timezone
from pathlib import Path

from api_client import REPO_ROOT

LKS_ID = 8244
STANDINGS_FILE = REPO_ROOT / "data" / "i_liga_standing.json"
SEASON_FILE = REPO_ROOT / "data" / "lks_current_season.json"
OUTPUT = REPO_ROOT / "data" / "dashboard.json"


def result_for_lks(match):
    is_home = str(match.get("homeTeamId")) == str(LKS_ID)
    gf = match.get("homeTeamScore") if is_home else match.get("awayTeamScore")
    ga = match.get("awayTeamScore") if is_home else match.get("homeTeamScore")
    if gf is None or ga is None:
        return None
    if gf > ga:
        return "W"
    if gf < ga:
        return "L"
    return "D"


def main():
    standings_doc = json.loads(STANDINGS_FILE.read_text(encoding="utf-8"))
    season_doc = json.loads(SEASON_FILE.read_text(encoding="utf-8"))

    standings = standings_doc["payload"]["response"]["standing"]
    matches = season_doc["matches"]
    finished = [m for m in matches if (m.get("status") or {}).get("finished")]

    lks = next(row for row in standings if row.get("id") == LKS_ID)

    gf = ga = clean_sheets = scored_matches = 0
    home = {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    away = {"played": 0, "wins": 0, "draws": 0, "losses": 0, "gf": 0, "ga": 0}
    best_win = None
    worst_loss = None

    for match in finished:
        is_home = str(match.get("homeTeamId")) == str(LKS_ID)
        mgf = match.get("homeTeamScore") if is_home else match.get("awayTeamScore")
        mga = match.get("awayTeamScore") if is_home else match.get("homeTeamScore")
        bucket = home if is_home else away
        result = result_for_lks(match)

        gf += mgf
        ga += mga
        bucket["played"] += 1
        bucket["gf"] += mgf
        bucket["ga"] += mga

        if result == "W":
            bucket["wins"] += 1
        elif result == "D":
            bucket["draws"] += 1
        elif result == "L":
            bucket["losses"] += 1

        if mga == 0:
            clean_sheets += 1
        if mgf > 0:
            scored_matches += 1

        diff = mgf - mga
        summary = {
            "id": match.get("id"),
            "date": match.get("matchDate"),
            "homeTeamName": match.get("homeTeamName"),
            "awayTeamName": match.get("awayTeamName"),
            "score": (match.get("status") or {}).get("scoreStr"),
            "goalDiff": diff,
        }

        if diff > 0 and (best_win is None or diff > best_win["goalDiff"]):
            best_win = summary
        if diff < 0 and (worst_loss is None or diff < worst_loss["goalDiff"]):
            worst_loss = summary

    parsed = []
    for row in standings:
        team_gf, team_ga = [int(x) for x in row["scoresStr"].split("-")]
        parsed.append({**row, "gf": team_gf, "ga": team_ga})

    max_gf = max(row["gf"] for row in parsed)
    min_ga = min(row["ga"] for row in parsed)
    max_ga = max(row["ga"] for row in parsed)

    form = []
    for match in finished[-5:]:
        opponent = (
            match.get("awayTeamName")
            if str(match.get("homeTeamId")) == str(LKS_ID)
            else match.get("homeTeamName")
        )
        form.append({
            "result": result_for_lks(match),
            "opponent": opponent,
            "score": (match.get("status") or {}).get("scoreStr"),
            "date": match.get("matchDate"),
        })

    dashboard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "team": {"id": LKS_ID, "name": "ŁKS Łódź", "league": "I Liga", "season": "2026/27"},
        "summary": {
            "position": lks["idx"],
            "points": lks["pts"],
            "played": lks["played"],
            "wins": lks["wins"],
            "draws": lks["draws"],
            "losses": lks["losses"],
            "goals_for": gf,
            "goals_against": ga,
            "goal_difference": gf - ga,
            "points_per_match": round(lks["pts"] / lks["played"], 2),
            "goals_for_per_match": round(gf / len(finished), 2),
            "goals_against_per_match": round(ga / len(finished), 2),
            "clean_sheets": clean_sheets,
            "matches_scored_in": scored_matches,
        },
        "form": form,
        "splits": {"home": home, "away": away},
        "records": {"best_win": best_win, "worst_loss": worst_loss},
        "previous_match": season_doc.get("previous_match"),
        "next_match": season_doc.get("next_match"),
        "upcoming_matches": [
            m for m in matches if not (m.get("status") or {}).get("finished")
        ][:6],
        "league_leaders": {
            "best_attack": [
                {"name": row["name"], "value": row["gf"]}
                for row in parsed if row["gf"] == max_gf
            ],
            "best_defense": [
                {"name": row["name"], "value": row["ga"]}
                for row in parsed if row["ga"] == min_ga
            ],
            "most_goals_conceded": [
                {"name": row["name"], "value": row["ga"]}
                for row in parsed if row["ga"] == max_ga
            ],
        },
        "standings": [
            {
                "position": row["idx"],
                "id": row["id"],
                "name": row["name"],
                "played": row["played"],
                "wins": row["wins"],
                "draws": row["draws"],
                "losses": row["losses"],
                "goals": row["scoresStr"],
                "goal_difference": row["goalConDiff"],
                "points": row["pts"],
                "qualColor": row.get("qualColor"),
            }
            for row in standings
        ],
    }

    OUTPUT.write_text(
        json.dumps(dashboard, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Zapisano: {OUTPUT.relative_to(REPO_ROOT)}")
    print("Ten skrypt NIE wykonuje requestu do RapidAPI.")


if __name__ == "__main__":
    main()
