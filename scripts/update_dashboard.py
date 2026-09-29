import argparse
import json
from datetime import datetime, timezone

from api_client import REPO_ROOT, call_api
from build_current_season import main as build_current_season
from build_dashboard_stats import main as build_dashboard_stats

LEAGUE_ID = 197
LKS_ID = 8244

STANDINGS_ENDPOINT = "/football-get-standing-all"
MATCH_SEARCH_ENDPOINT = "/football-matches-search"

STANDINGS_FILE = REPO_ROOT / "data" / "i_liga_standing.json"
MATCH_SEARCH_FILE = REPO_ROOT / "data" / "lks_match_search.json"


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def find_lks(rows):
    for row in rows:
        if str(row.get("id")) == str(LKS_ID):
            return row
    return None


def refresh_standings():
    print("1/2 Tabela I ligi: pobieram...")
    result = call_api(
        STANDINGS_ENDPOINT,
        {"leagueid": LEAGUE_ID},
    )

    payload = result["data"]
    meta = result["meta"]
    rows = (
        payload.get("response", {}).get("standing", [])
        if isinstance(payload, dict)
        else []
    )

    if payload.get("status") != "success" or not isinstance(rows, list) or not rows:
        raise RuntimeError(
            "Endpoint tabeli nie zwrócił poprawnych danych; "
            "stary cache nie został nadpisany."
        )

    lks_row = find_lks(rows)
    if lks_row is None:
        raise RuntimeError(
            "W tabeli nie znaleziono ŁKS (team id 8244); "
            "stary cache nie został nadpisany."
        )

    output = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": STANDINGS_ENDPOINT,
        "league_id": LEAGUE_ID,
        "rapidapi_limit": meta["limit"],
        "rapidapi_remaining": meta["remaining"],
        "rapidapi_reset": meta["reset"],
        "lks_found": True,
        "lks": lks_row,
        "payload": payload,
    }
    save_json(STANDINGS_FILE, output)

    print(
        f"   OK: ŁKS {lks_row.get('idx')}. miejsce, "
        f"{lks_row.get('pts')} pkt; "
        f"limit {meta['remaining']} / {meta['limit']}"
    )


def refresh_matches():
    print("Terminarz ŁKS: pobieram...")
    result = call_api(
        MATCH_SEARCH_ENDPOINT,
        {"search": "lks"},
    )

    payload = result["data"]
    meta = result["meta"]
    suggestions = (
        payload.get("response", {}).get("suggestions", [])
        if isinstance(payload, dict)
        else []
    )

    if (
        payload.get("status") != "success"
        or not isinstance(suggestions, list)
        or not suggestions
    ):
        raise RuntimeError(
            "Endpoint wyszukiwania meczów nie zwrócił poprawnych danych; "
            "stary cache nie został nadpisany."
        )

    output = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": MATCH_SEARCH_ENDPOINT,
        "search": "lks",
        "rapidapi_limit": meta["limit"],
        "rapidapi_remaining": meta["remaining"],
        "rapidapi_reset": meta["reset"],
        "payload": payload,
    }
    save_json(MATCH_SEARCH_FILE, output)

    print(
        f"   OK: {len(suggestions)} sugestii; "
        f"limit {meta['remaining']} / {meta['limit']}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Odświeża dane dashboardu ŁKS i przebudowuje pliki pochodne."
    )
    parser.add_argument(
        "--mode",
        choices=("full", "matches"),
        default="full",
        help=(
            "full = tabela + terminarz (2 requesty); "
            "matches = tylko terminarz (1 request)"
        ),
    )
    args = parser.parse_args()

    print(f"Tryb aktualizacji: {args.mode}")
    if args.mode == "full":
        print("Plan: dokładnie 2 requesty do RapidAPI.")
        refresh_standings()
    else:
        print("Plan: dokładnie 1 request do RapidAPI.")

    refresh_matches()

    print("Przebudowuję bieżący sezon...")
    build_current_season()

    print("Przebudowuję dashboard...")
    build_dashboard_stats()

    print("Aktualizacja zakończona.")


if __name__ == "__main__":
    main()
