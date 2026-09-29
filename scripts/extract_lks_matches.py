import json
from datetime import datetime, timezone
from pathlib import Path

from api_client import REPO_ROOT

LKS_ID = 8244
SOURCE = REPO_ROOT / "data" / "i_liga_matches.json"
OUTPUT = REPO_ROOT / "data" / "lks_matches.json"


def as_team_id(value):
    if value is None:
        return None
    return str(value)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Brak pliku: {SOURCE}")

    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    matches = (
        doc.get("payload", {})
        .get("response", {})
        .get("matches", [])
    )

    if not isinstance(matches, list):
        raise RuntimeError("Nieoczekiwana struktura: payload.response.matches nie jest listą.")

    lks_matches = []
    seen = set()

    for match in matches:
        if not isinstance(match, dict):
            continue

        home_id = as_team_id((match.get("home") or {}).get("id"))
        away_id = as_team_id((match.get("away") or {}).get("id"))

        if str(LKS_ID) not in (home_id, away_id):
            continue

        match_id = str(match.get("id"))
        if match_id in seen:
            continue

        seen.add(match_id)
        lks_matches.append(match)

    lks_matches.sort(
        key=lambda m: ((m.get("status") or {}).get("utcTime") or "")
    )

    now = datetime.now(timezone.utc)

    def match_time(match):
        raw = (match.get("status") or {}).get("utcTime")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    past = []
    future = []
    for match in lks_matches:
        dt = match_time(match)
        if dt is None:
            continue
        if dt <= now:
            past.append(match)
        else:
            future.append(match)

    result = {
        "generated_at_utc": now.isoformat(),
        "source_file": "data/i_liga_matches.json",
        "source_updated_at_utc": doc.get("updated_at_utc"),
        "league_id": doc.get("league_id"),
        "lks_id": LKS_ID,
        "match_count": len(lks_matches),
        "first_match": lks_matches[0] if lks_matches else None,
        "last_match_in_source": lks_matches[-1] if lks_matches else None,
        "previous_match": past[-1] if past else None,
        "next_match": future[0] if future else None,
        "matches": lks_matches,
    }

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Unikalne mecze ŁKS: {len(lks_matches)}")
    if lks_matches:
        print(
            "Zakres źródła:",
            (lks_matches[0].get("status") or {}).get("utcTime"),
            "->",
            (lks_matches[-1].get("status") or {}).get("utcTime"),
        )
    print("Następny mecz w tym źródle:", "TAK" if future else "BRAK")
    print(f"Zapisano: {OUTPUT.relative_to(REPO_ROOT)}")
    print("Ten skrypt NIE wykonuje żadnego requestu do RapidAPI.")


if __name__ == "__main__":
    main()
