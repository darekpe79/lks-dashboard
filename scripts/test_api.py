import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

HOST = "free-api-live-football-data.p.rapidapi.com"
ENDPOINT = "/football-get-standing-all"
LEAGUE_ID = 197
LKS_ID = 8244

API_KEY = os.environ.get("RAPIDAPI_KEY")
if not API_KEY:
    raise RuntimeError("Brak zmiennej środowiskowej RAPIDAPI_KEY")

params = urlencode({"leagueid": LEAGUE_ID})
url = f"https://{HOST}{ENDPOINT}?{params}"

request = Request(
    url,
    headers={
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": HOST,
    },
    method="GET",
)

try:
    with urlopen(request, timeout=30) as response:
        status = response.status
        raw = response.read().decode("utf-8")
        headers = response.headers
except HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    raise RuntimeError(f"RapidAPI zwróciło HTTP {exc.code}: {body[:1000]}") from exc
except URLError as exc:
    raise RuntimeError(f"Błąd połączenia z RapidAPI: {exc}") from exc

if status != 200:
    raise RuntimeError(f"Nieoczekiwany status HTTP: {status}")

try:
    payload = json.loads(raw)
except json.JSONDecodeError as exc:
    raise RuntimeError(f"Odpowiedź nie jest poprawnym JSON-em: {raw[:1000]}") from exc


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
        if "ŁKS" in name or "LKS" in name.upper():
            if "ŁÓDŹ" in name.upper() or "LODZ" in name.upper():
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


lks_row = find_lks(payload)

remaining = headers.get("x-ratelimit-requests-remaining")
limit = headers.get("x-ratelimit-requests-limit")
reset = headers.get("x-ratelimit-requests-reset")

result = {
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    "endpoint": ENDPOINT,
    "league_id": LEAGUE_ID,
    "rapidapi_limit": limit,
    "rapidapi_remaining": remaining,
    "rapidapi_reset": reset,
    "lks_found": lks_row is not None,
    "lks": lks_row,
    "payload": payload,
}

out = Path("data") / "i_liga_standing.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"HTTP: {status}")
print(f"RapidAPI remaining: {remaining} / {limit}")
print(f"ŁKS znaleziony: {'TAK' if lks_row else 'NIE'}")
if lks_row:
    print(json.dumps(lks_row, ensure_ascii=False, indent=2)[:2000])
print(f"Zapisano: {out}")
