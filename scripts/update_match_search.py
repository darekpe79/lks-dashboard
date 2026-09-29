import json
from datetime import datetime, timezone

from api_client import REPO_ROOT, call_api

ENDPOINT = "/football-matches-search"
SEARCH = "lks"


def main():
    print("Szukam meczów ŁKS przez endpoint wyszukiwania...")
    print("To uruchomienie wykona dokładnie 1 request do RapidAPI.")

    result = call_api(
        ENDPOINT,
        {"search": SEARCH},
    )

    meta = result["meta"]
    output = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": ENDPOINT,
        "search": SEARCH,
        "rapidapi_limit": meta["limit"],
        "rapidapi_remaining": meta["remaining"],
        "rapidapi_reset": meta["reset"],
        "payload": result["data"],
    }

    out = REPO_ROOT / "data" / "lks_match_search.json"
    out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"HTTP: {meta['status_code']}")
    print(f"RapidAPI remaining: {meta['remaining']} / {meta['limit']}")
    print(f"Zapisano: {out.relative_to(REPO_ROOT)}")
    print("Po pushu sprawdzimy strukturę i czy endpoint pokazuje bieżący sezon.")


if __name__ == "__main__":
    main()
