import json
from datetime import datetime, timezone

from api_client import REPO_ROOT, call_api

ENDPOINT = "/football-get-all-matches-by-league"
LEAGUE_ID = 197
LKS_ID = 8244
LKS_NAMES = ("ŁKS ŁÓDŹ", "LKS LODZ", "ŁKS LODZ", "LKS ŁÓDŹ")


def looks_like_lks(value):
    if value is None:
        return False

    if isinstance(value, (int, float)):
        return str(int(value)) == str(LKS_ID)

    text = str(value).strip().upper()
    return text in LKS_NAMES or "ŁKS ŁÓDŹ" in text or "LKS LODZ" in text


def object_mentions_lks(obj):
    if not isinstance(obj, dict):
        return False

    id_keys = (
        "id",
        "teamid",
        "teamId",
        "team_id",
        "homeTeamId",
        "awayTeamId",
        "homeTeamID",
        "awayTeamID",
        "home_id",
        "away_id",
    )
    for key in id_keys:
        if key in obj and looks_like_lks(obj.get(key)):
            return True

    name_keys = (
        "name",
        "teamName",
        "homeTeam",
        "awayTeam",
        "home",
        "away",
        "homeName",
        "awayName",
        "homeTeamName",
        "awayTeamName",
    )
    for key in name_keys:
        value = obj.get(key)
        if isinstance(value, str) and looks_like_lks(value):
            return True
        if isinstance(value, dict) and object_mentions_lks(value):
            return True

    return False


def collect_lks_match_candidates(obj):
    """
    Collect dictionaries that appear to describe an ŁKS match.
    We deliberately keep this permissive because the API response shape
    may change. The full raw payload is always saved as well.
    """
    candidates = []

    def walk(value):
        if isinstance(value, dict):
            if object_mentions_lks(value):
                # Prefer objects that look match-like.
                keys = {str(k).lower() for k in value.keys()}
                match_markers = (
                    "eventid",
                    "event_id",
                    "matchid",
                    "match_id",
                    "hometeam",
                    "awayteam",
                    "hometeamid",
                    "awayteamid",
                    "starttimestamp",
                    "status",
                    "score",
                    "round",
                )
                if any(marker in keys for marker in match_markers):
                    candidates.append(value)

            for nested in value.values():
                walk(nested)

        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(obj)

    # Remove exact duplicates while preserving order.
    unique = []
    seen = set()
    for item in candidates:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            unique.append(item)

    return unique


def main():
    print("Pobieram wszystkie mecze I ligi...")
    print("To uruchomienie wykona dokładnie 1 request do RapidAPI.")

    result = call_api(
        ENDPOINT,
        {"leagueid": LEAGUE_ID},
    )

    meta = result["meta"]
    payload = result["data"]
    lks_matches = collect_lks_match_candidates(payload)

    output = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": ENDPOINT,
        "league_id": LEAGUE_ID,
        "lks_id": LKS_ID,
        "rapidapi_limit": meta["limit"],
        "rapidapi_remaining": meta["remaining"],
        "rapidapi_reset": meta["reset"],
        "lks_match_candidates_count": len(lks_matches),
        "lks_match_candidates": lks_matches,
        "payload": payload,
    }

    out = REPO_ROOT / "data" / "i_liga_matches.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"HTTP: {meta['status_code']}")
    print(f"RapidAPI remaining: {meta['remaining']} / {meta['limit']}")
    print(f"Znalezione kandydaty meczów ŁKS: {len(lks_matches)}")
    print(f"Zapisano: {out.relative_to(REPO_ROOT)}")

    if lks_matches:
        print("\nPierwszy znaleziony kandydat:")
        print(json.dumps(lks_matches[0], ensure_ascii=False, indent=2)[:3000])
    else:
        print(
            "\nNie udało się automatycznie rozpoznać meczów ŁKS. "
            "To nie jest błąd krytyczny — pełna odpowiedź API została zapisana "
            "w data/i_liga_matches.json i możemy przeanalizować jej strukturę."
        )


if __name__ == "__main__":
    main()
