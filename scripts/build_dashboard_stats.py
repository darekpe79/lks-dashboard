import json
from datetime import datetime, timezone

from api_client import REPO_ROOT

LKS_ID = 8244
STANDINGS_FILE = REPO_ROOT / "data" / "i_liga_standing.json"
SEASON_FILE = REPO_ROOT / "data" / "lks_current_season.json"
OUTPUT = REPO_ROOT / "data" / "dashboard.json"
CONTEXT_FILE = REPO_ROOT / "data" / "context.json"


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


def longest_streak(results, wanted):
    best = current = 0
    for result in results:
        if result == wanted:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def longest_unbeaten(results):
    best = current = 0
    for result in results:
        if result in ("W", "D"):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def main():
    standings_doc = json.loads(STANDINGS_FILE.read_text(encoding="utf-8"))
    season_doc = json.loads(SEASON_FILE.read_text(encoding="utf-8"))
    context_doc = (
        json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        if CONTEXT_FILE.exists()
        else {}
    )

    standings = standings_doc["payload"]["response"]["standing"]
    matches = season_doc["matches"]
    finished = sorted(
        [m for m in matches if (m.get("status") or {}).get("finished")],
        key=lambda m: m.get("matchDate", ""),
    )

    lks = next(row for row in standings if row.get("id") == LKS_ID)

    home = {
        "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "gf": 0, "ga": 0, "clean_sheets": 0, "failed_to_score": 0,
        "max_gf": 0, "max_ga": 0, "biggest_win_margin": 0, "biggest_loss_margin": 0,
    }
    away = {
        "played": 0, "wins": 0, "draws": 0, "losses": 0,
        "gf": 0, "ga": 0, "clean_sheets": 0, "failed_to_score": 0,
        "max_gf": 0, "max_ga": 0, "biggest_win_margin": 0, "biggest_loss_margin": 0,
    }

    gf = ga = clean_sheets = scored_matches = failed_to_score = 0
    best_win = None
    worst_loss = None
    result_sequence = []

    for match in finished:
        is_home = str(match.get("homeTeamId")) == str(LKS_ID)
        mgf = match.get("homeTeamScore") if is_home else match.get("awayTeamScore")
        mga = match.get("awayTeamScore") if is_home else match.get("homeTeamScore")
        bucket = home if is_home else away
        result = result_for_lks(match)
        result_sequence.append(result)

        gf += mgf
        ga += mga
        bucket["played"] += 1
        bucket["gf"] += mgf
        bucket["ga"] += mga
        bucket["max_gf"] = max(bucket["max_gf"], mgf)
        bucket["max_ga"] = max(bucket["max_ga"], mga)

        if result == "W":
            bucket["wins"] += 1
        elif result == "D":
            bucket["draws"] += 1
        elif result == "L":
            bucket["losses"] += 1

        if mga == 0:
            clean_sheets += 1
            bucket["clean_sheets"] += 1

        if mgf > 0:
            scored_matches += 1
        else:
            failed_to_score += 1
            bucket["failed_to_score"] += 1

        diff = mgf - mga
        if diff > 0:
            bucket["biggest_win_margin"] = max(bucket["biggest_win_margin"], diff)
        if diff < 0:
            bucket["biggest_loss_margin"] = max(bucket["biggest_loss_margin"], abs(diff))

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

    for bucket in (home, away):
        played = bucket["played"]
        bucket["gf_avg"] = round(bucket["gf"] / played, 2) if played else 0
        bucket["ga_avg"] = round(bucket["ga"] / played, 2) if played else 0

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

    next_match = season_doc.get("next_match")
    next_opponent = None
    if next_match:
        opponent_id = (
            next_match.get("awayTeamId")
            if str(next_match.get("homeTeamId")) == str(LKS_ID)
            else next_match.get("homeTeamId")
        )
        opponent_name = (
            next_match.get("awayTeamName")
            if str(next_match.get("homeTeamId")) == str(LKS_ID)
            else next_match.get("homeTeamName")
        )
        opponent_row = next(
            (row for row in parsed if str(row.get("id")) == str(opponent_id)),
            None,
        )
        if opponent_row:
            next_opponent = {
                "id": opponent_row["id"],
                "name": opponent_name,
                "position": opponent_row["idx"],
                "points": opponent_row["pts"],
                "played": opponent_row["played"],
                "wins": opponent_row["wins"],
                "draws": opponent_row["draws"],
                "losses": opponent_row["losses"],
                "goals_for": opponent_row["gf"],
                "goals_against": opponent_row["ga"],
                "goal_difference": opponent_row["goalConDiff"],
                "points_gap_to_lks": opponent_row["pts"] - lks["pts"],
                "position_gap_to_lks": opponent_row["idx"] - lks["idx"],
                "venue": (
                    "home"
                    if str(next_match.get("homeTeamId")) == str(LKS_ID)
                    else "away"
                ),
            }

            if str(context_doc.get("opponent_id")) == str(opponent_id):
                next_opponent["profile"] = context_doc.get("opponent_profile")
                next_opponent["home_standing"] = (
                    context_doc.get("home_standing", {}).get("opponent")
                )
                next_opponent["away_standing"] = (
                    context_doc.get("away_standing", {}).get("opponent")
                )
                next_opponent["h2h"] = context_doc.get("h2h", [])

    team_context = {
        "id": LKS_ID,
        "name": "ŁKS Łódź",
        "league": "I Liga",
        "season": "2026/27",
        "profile": context_doc.get("lks_profile"),
        "home_standing": context_doc.get("home_standing", {}).get("lks"),
        "away_standing": context_doc.get("away_standing", {}).get("lks"),
    }

    dashboard = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "team": team_context,
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
            "goals_for_per_match": round(gf / len(finished), 2) if finished else 0,
            "goals_against_per_match": round(ga / len(finished), 2) if finished else 0,
            "clean_sheets": clean_sheets,
            "matches_scored_in": scored_matches,
            "failed_to_score": failed_to_score,
        },
        "form": form,
        "splits": {"home": home, "away": away},
        "records": {
            "best_win": best_win,
            "worst_loss": worst_loss,
            "streaks": {
                "wins": longest_streak(result_sequence, "W"),
                "draws": longest_streak(result_sequence, "D"),
                "losses": longest_streak(result_sequence, "L"),
                "unbeaten": longest_unbeaten(result_sequence),
            },
            "biggest_goals": {
                "for": {"home": home["max_gf"], "away": away["max_gf"]},
                "against": {"home": home["max_ga"], "away": away["max_ga"]},
            },
        },
        "previous_match": season_doc.get("previous_match"),
        "next_match": next_match,
        "next_opponent": next_opponent,
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
