import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from api_client import REPO_ROOT

FILES = {
    "matches": [REPO_ROOT / "data" / "lks_match_search.json"],
    "full": [
        REPO_ROOT / "data" / "lks_match_search.json",
        REPO_ROOT / "data" / "i_liga_standing.json",
    ],
}


def read_updated_at(path: Path):
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        value = doc.get("updated_at_utc")
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (json.JSONDecodeError, ValueError, OSError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("matches", "full"), required=True)
    parser.add_argument("--max-age-hours", type=float, default=7.0)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    stale = []

    for path in FILES[args.mode]:
        updated = read_updated_at(path)
        if updated is None:
            stale.append(f"{path.name}: brak poprawnego updated_at_utc")
            continue

        age_hours = (now - updated).total_seconds() / 3600
        if age_hours >= args.max_age_hours:
            stale.append(f"{path.name}: {age_hours:.2f} h")

    if stale:
        print("Odświeżenie potrzebne: " + "; ".join(stale))
        raise SystemExit(0)

    print(
        f"Dane dla trybu {args.mode} są młodsze niż "
        f"{args.max_age_hours:g} h — pomijam RapidAPI."
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
