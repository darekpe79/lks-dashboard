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
        description="Jednorazowe testy dodatkowych endpointów dashboardu ŁKS."
    )
    parser.add_argument(
        "mode",
        choices=("opponent", "h2h", "home", "away", "logo", "location"),
        help=(
            "opponent = wyszukiwanie meczów najbliższego rywala; "
            "h2h = bezpośrednie mecze; "
            "home/away = tabela domowa/wyjazdowa; "
            "logo = logo najbliższego rywala; "
            "location = miejsce następnego meczu"
        ),
    )
    args = parser.parse_args()

    ctx = load_context()

    tests = {
        "opponent": (
            "/football-matches-search",
            {"search": ctx["opponent_name"]},
        ),
        "h2h": (
            "/football-get-head-to-head",
            {"eventid": ctx["event_id"]},
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
            {"teamid": ctx["opponent_id"]},
        ),
        "location": (
            "/football-get-match-location",
            {"eventid": ctx["event_id"]},
        ),
    }

    endpoint, params = tests[args.mode]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / f"probe_{safe_name(args.mode)}.json"

    print(f"Tryb: {args.mode}")
    print(f"Najbliższy rywal: {ctx['opponent_name']} (teamid={ctx['opponent_id']})")
    print(f"Następny mecz eventid={ctx['event_id']}")
    print(f"Endpoint: {endpoint}")
    print(f"Parametry: {params}")
    print("To uruchomienie wykona dokładnie 1 request do RapidAPI.")

    result = call_api(endpoint, params=params, save_to=output)
    meta = result["meta"]

    print(f"HTTP: {meta['status_code']}")
    print(f"RapidAPI remaining: {meta['remaining']} / {meta['limit']}")
    print(f"Zapisano: {output.relative_to(REPO_ROOT)}")
    print("Podgląd odpowiedzi:")
    print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:3500])


if __name__ == "__main__":
    main()
