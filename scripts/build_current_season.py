import json
from datetime import datetime, timezone

from api_client import REPO_ROOT

SOURCE = REPO_ROOT / "data" / "lks_match_search.json"
OUTPUT = REPO_ROOT / "data" / "lks_current_season.json"

LKS_ID = "8244"
LEAGUE_ID = 197
SEASON_START = "2026-07-01T00:00:00Z"


def main():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    suggestions = (
        doc.get("payload", {})
        .get("response", {})
        .get("suggestions", [])
    )

    matches = [
        m for m in suggestions
        if isinstance(m, dict)
        and m.get("type") == "match"
        and m.get("leagueId") == LEAGUE_ID
        and m.get("matchDate", "") >= SEASON_START
        and (
            str(m.get("homeTeamId")) == LKS_ID
            or str(m.get("awayTeamId")) == LKS_ID
        )
    ]

    # Deduplicate by event id and sort chronologically.
    dedup = {}
    for match in matches:
        dedup[str(match.get("id"))] = match

    matches = sorted(
        dedup.values(),
        key=lambda m: m.get("matchDate", "")
    )

    now = datetime.now(timezone.utc)

    def parse_dt(raw):
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))

    past = [
        m for m in matches
        if m.get("matchDate") and parse_dt(m["matchDate"]) <= now
    ]
    future = [
        m for m in matches
        if m.get("matchDate") and parse_dt(m["matchDate"]) > now
    ]

    result = {
        "generated_at_utc": now.isoformat(),
        "source_file": "data/lks_match_search.json",
        "source_updated_at_utc": doc.get("updated_at_utc"),
        "team_id": int(LKS_ID),
        "league_id": LEAGUE_ID,
        "season_start": SEASON_START,
        "match_count": len(matches),
        "previous_match": past[-1] if past else None,
        "next_match": future[0] if future else None,
        "matches": matches,
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Mecze ŁKS w bieżącym sezonie znalezione w search: {len(matches)}")
    if result["previous_match"]:
        m = result["previous_match"]
        print(
            "Ostatni:",
            m.get("homeTeamName"),
            m.get("status", {}).get("scoreStr", "-"),
            m.get("awayTeamName"),
            f"(eventid={m.get('id')})"
        )
    if result["next_match"]:
        m = result["next_match"]
        print(
            "Następny:",
            m.get("homeTeamName"),
            "-",
            m.get("awayTeamName"),
            m.get("matchDate"),
            f"(eventid={m.get('id')})"
        )

    print(f"Zapisano: {OUTPUT.relative_to(REPO_ROOT)}")
    print("Ten skrypt NIE wykonuje requestu do RapidAPI.")


if __name__ == "__main__":
    main()
