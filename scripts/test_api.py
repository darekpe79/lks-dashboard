import json
from datetime import datetime, timezone
from pathlib import Path

from api_client import REPO_ROOT, call_api

ENDPOINT = "/football-get-standing-all"
LEAGUE_ID = 197
LKS_ID = 8244


def find_lks(obj):
    if isinstance(obj, dict):
        possible_ids = (
            obj.get("id"),
            obj.get("teamid"),
            obj.get("teamId"),
            obj.get("team_id"),
        )
        if any(str(value) == str(LKS_ID) for value in possible_ids if value is not None):
            return obj

        name = str(obj.get("name", ""))
        name_upper = name.upper()
        if ("ŁKS" in name_upper or "LKS" in name_upper) and (
            "ŁÓDŹ" in name_upper or "LODZ" in name_upper
        ):
            return obj

        for value in obj.values():
            found = find_lks(value)
            if found is not None:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = find_lks(item)
            if found is not None:
                return found

    return None


result = call_api(
    ENDPOINT,
    {"leagueid": LEAGUE_ID},
)

payload = result["data"]
meta = result["meta"]
lks_row = find_lks(payload)

output = {
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    "endpoint": ENDPOINT,
    "league_id": LEAGUE_ID,
    "rapidapi_limit": meta["limit"],
    "rapidapi_remaining": meta["remaining"],
    "rapidapi_reset": meta["reset"],
    "lks_found": lks_row is not None,
    "lks": lks_row,
    "payload": payload,
}

out = REPO_ROOT / "data" / "i_liga_standing.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"HTTP: {meta['status_code']}")
print(f"RapidAPI remaining: {meta['remaining']} / {meta['limit']}")
print(f"ŁKS znaleziony: {'TAK' if lks_row else 'NIE'}")
if lks_row:
    print(json.dumps(lks_row, ensure_ascii=False, indent=2)[:2000])
print(f"Zapisano: {out.relative_to(REPO_ROOT)}")
