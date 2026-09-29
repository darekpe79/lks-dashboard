import json

from api_client import REPO_ROOT, call_api

SOURCE = REPO_ROOT / "data" / "lks_current_season.json"
OUTPUT = REPO_ROOT / "data" / "latest_match_stats.json"
ENDPOINT = "/football-get-match-event-all-stats"


def main():
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    previous = doc.get("previous_match")

    if not previous:
        raise RuntimeError("Brak previous_match w data/lks_current_season.json")

    event_id = previous.get("id")
    if not event_id:
        raise RuntimeError("Brak event id w previous_match")

    print(
        "Pobieram pełne statystyki ostatniego meczu:",
        previous.get("homeTeamName"),
        "vs",
        previous.get("awayTeamName"),
        f"(eventid={event_id})",
    )
    print("To uruchomienie wykona dokładnie 1 request do RapidAPI.")

    result = call_api(
        ENDPOINT,
        {"eventid": event_id},
    )

    output = {
        "event_id": event_id,
        "source_match": previous,
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
