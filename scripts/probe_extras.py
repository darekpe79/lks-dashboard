import argparse
import json
import re

from api_client import REPO_ROOT, call_api

CURRENT_SEASON = REPO_ROOT / "data" / "lks_current_season.json"
OUTPUT_DIR = REPO_ROOT / "api_tests"
LKS_ID = 8244
LEAGUE_ID = 197


def load_context():
    doc = json.loads(CURRENT_SEASON.read_text(encoding="utf-8"))
    next_match = doc.get("next_match")
    if not next_match:
        raise RuntimeError("Brak next_match w data/lks_current_season.json")

    if str(next_match.get("homeTeamId")) == str(LKS_ID):
        opponent_id = next_match.get("awayTeamId")
        opponent_name = next_match.get("awayTeamName")
    else:
        opponent_id = next_match.get("homeTeamId")
        opponent_name = next_match.get("homeTeamName")

    return {
        "event_id": next_match.get("id"),
        "opponent_id": opponent_id,
        "opponent_name": opponent_name,
    }


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Jednorazowe testy endpointów Free API Live Football Data. "
            "Każde uruchomienie wykonuje dokładnie 1 request."
        )
    )
    parser.add_argument(
        "mode",
        choices=(
            "teaminfo",
            "rounds",
            "rounddetail",
            "h2h",
            "home",
            "away",
            "logo",
            "location",
            "matchdetail",
            "score",
            "status",
            "referee",
            "highlights",
            "homelineup",
            "awaylineup",
            "eventstats",
            "allstats",
            "players",
            "opponent-search",
        ),
    )
    parser.add_argument(
        "--round-id",
        help="ID rundy wymagane dla trybu rounddetail.",
    )
    parser.add_argument(
        "--team",
        choices=("opponent", "lks"),
        default="opponent",
        help="Którego teamid użyć w trybach drużynowych (domyślnie opponent).",
    )
    args = parser.parse_args()

    ctx = load_context()
    team_id = LKS_ID if args.team == "lks" else ctx["opponent_id"]

    if args.mode == "rounddetail" and not args.round_id:
        parser.error("Tryb rounddetail wymaga --round-id ID")

    tests = {
        # Endpointy po teamid / leagueid — najciekawsze dla statystyk rywala bez stringów.
        "teaminfo": (
            "/football-league-team",
            {"teamid": team_id},
        ),
        "rounds": (
            "/football-get-all-rounds",
            {"leagueid": LEAGUE_ID},
        ),
        "rounddetail": (
            "/football-get-rounds-detail",
            {"roundid": args.round_id},
        ),
        "home": (
            "/football-get-standing-home",
            {"leagueid": LEAGUE_ID},
        ),
        "away": (
            "/football-get-standing-away",
            {"leagueid": LEAGUE_ID},
        ),
        "logo": (
            "/football-team-logo",
            {"teamid": team_id},
        ),
        "players": (
            "/football-get-list-player",
            {"teamid": team_id},
        ),

        # Endpointy po eventid następnego meczu.
        "h2h": (
            "/football-get-head-to-head",
            {"eventid": ctx["event_id"]},
        ),
        "location": (
            "/football-get-match-location",
            {"eventid": ctx["event_id"]},
        ),
        "matchdetail": (
            "/football-get-match-detail",
            {"eventid": ctx["event_id"]},
        ),
        "score": (
            "/football-get-match-score",
            {"eventid": ctx["event_id"]},
        ),
        "status": (
            "/football-get-match-status",
            {"eventid": ctx["event_id"]},
        ),
        "referee": (
            "/football-get-match-referee",
            {"eventid": ctx["event_id"]},
        ),
        "highlights": (
            "/football-get-match-highlights",
            {"eventid": ctx["event_id"]},
        ),
        "homelineup": (
            "/football-get-hometeam-lineup",
            {"eventid": ctx["event_id"]},
        ),
        "awaylineup": (
            "/football-get-awayteam-lineup",
            {"eventid": ctx["event_id"]},
        ),
        "eventstats": (
            "/football-get-match-event-all-stats",
            {"eventid": ctx["event_id"]},
        ),
        "allstats": (
            "/football-get-match-all-stats",
            {"eventid": ctx["event_id"]},
        ),

        # Tylko kontrolny fallback — jako jedyny korzysta z tekstowego search.
        "opponent-search": (
            "/football-matches-search",
            {"search": ctx["opponent_name"]},
        ),
    }

    endpoint, params = tests[args.mode]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.team}" if args.mode in {"teaminfo", "logo", "players"} else ""
    output = OUTPUT_DIR / f"probe_{safe_name(args.mode)}{suffix}.json"

    print(f"Tryb: {args.mode}")
    print(f"ŁKS teamid={LKS_ID}")
    print(
        f"Najbliższy rywal: {ctx['opponent_name']} "
        f"(teamid={ctx['opponent_id']})"
    )
    print(f"Następny mecz eventid={ctx['event_id']}")
    print(f"Endpoint: {endpoint}")
    print(f"Parametry: {params}")
    print("UWAGA: to uruchomienie wykona dokładnie 1 request do RapidAPI.")

    result = call_api(endpoint, params=params, save_to=output)
    meta = result["meta"]

    print(f"HTTP: {meta['status_code']}")
    print(f"RapidAPI remaining: {meta['remaining']} / {meta['limit']}")
    print(f"Zapisano: {output.relative_to(REPO_ROOT)}")
    print("Podgląd odpowiedzi:")
    print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:5000])


if __name__ == "__main__":
    main()
