import json
from datetime import datetime, timezone

from api_client import REPO_ROOT, call_api

ENDPOINT = "/football-get-list-player"
TEAM_ID = 8244
OUTPUT = REPO_ROOT / "data" / "lks_squad.json"


def main():
    print("Pobieram aktualną listę zawodników ŁKS Łódź...")
    print("To uruchomienie wykona dokładnie 1 request do RapidAPI.")

    result = call_api(
        ENDPOINT,
        {"teamid": TEAM_ID},
    )

    output = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": ENDPOINT,
        "team_id": TEAM_ID,
        "rapidapi": result["meta"],
        "payload": result["data"],
    }

    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"HTTP: {result['meta']['status_code']}")
    print(
        f"RapidAPI remaining: "
        f"{result['meta']['remaining']} / {result['meta']['limit']}"
    )
    print(f"Zapisano: {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
