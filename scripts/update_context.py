import json
import re
from datetime import datetime, timezone

from api_client import REPO_ROOT, call_api
from build_dashboard_stats import main as build_dashboard_stats

LKS_ID = 8244
LEAGUE_ID = 197

SEASON_FILE = REPO_ROOT / "data" / "lks_current_season.json"
CONTEXT_FILE = REPO_ROOT / "data" / "context.json"


def get_next_opponent():
    doc = json.loads(SEASON_FILE.read_text(encoding="utf-8"))
    match = doc.get("next_match")
    if not match:
        raise RuntimeError("Brak następnego meczu w data/lks_current_season.json")

    if str(match.get("homeTeamId")) == str(LKS_ID):
        opponent_id = int(match["awayTeamId"])
        opponent_name = match.get("awayTeamName")
    else:
        opponent_id = int(match["homeTeamId"])
        opponent_name = match.get("homeTeamName")

    return match, opponent_id, opponent_name


def api_payload(endpoint, params):
    result = call_api(endpoint, params)
    payload = result["data"]
    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise RuntimeError(f"{endpoint} nie zwrócił status=success: {payload}")
    return payload, result["meta"]


def extract_capacity(details):
    for item in details.get("faqJSONLD", {}).get("mainEntity", []):
        question = str(item.get("name", "")).lower()
        if "capacity" not in question:
            continue
        text = str(item.get("acceptedAnswer", {}).get("text", ""))
        numbers = re.findall(r"\b\d{4,6}\b", text.replace(",", ""))
        if numbers:
            return int(numbers[-1])
    return None


def extract_profile(payload):
    details = payload.get("response", {}).get("details") or {}
    sports = details.get("sportsTeamJSONLD") or {}
    location = sports.get("location") or {}
    address = location.get("address") or {}
    geo = location.get("geo") or {}

    return {
        "id": details.get("id"),
        "name": details.get("name"),
        "short_name": details.get("shortName"),
        "season": details.get("latestSeason"),
        "league_id": details.get("primaryLeagueId"),
        "league_name": details.get("primaryLeagueName"),
        "logo": sports.get("logo"),
        "stadium": location.get("name"),
        "city": address.get("addressLocality"),
        "country": address.get("addressCountry"),
        "capacity": extract_capacity(details),
        "latitude": geo.get("latitude"),
        "longitude": geo.get("longitude"),
    }


def get_standing(payload, team_id):
    rows = payload.get("response", {}).get("standing", [])
    row = next((x for x in rows if str(x.get("id")) == str(team_id)), None)
    if not row:
        return None
    return {
        "position": row.get("idx"),
        "played": row.get("played"),
        "wins": row.get("wins"),
        "draws": row.get("draws"),
        "losses": row.get("losses"),
        "goals": row.get("scoresStr"),
        "goal_difference": row.get("goalConDiff"),
        "points": row.get("pts"),
    }


def extract_h2h(payload):
    matches = payload.get("response", {}).get("lineup", {}).get("matches", [])
    finished = []
    for match in matches:
        status = match.get("status") or {}
        if not status.get("finished"):
            continue
        home = match.get("home") or {}
        away = match.get("away") or {}
        league = match.get("league") or {}
        finished.append({
            "date": (match.get("time") or {}).get("utcTime") or status.get("utcTime"),
            "league_id": league.get("id"),
            "league_name": league.get("name"),
            "home_id": home.get("id"),
            "home_name": home.get("name"),
            "away_id": away.get("id"),
            "away_name": away.get("name"),
            "score": status.get("scoreStr"),
        })

    finished.sort(key=lambda x: x.get("date") or "", reverse=True)
    return finished[:5]


def main():
    match, opponent_id, opponent_name = get_next_opponent()

    old = {}
    if CONTEXT_FILE.exists():
        old = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))

    calls = 0

    home_payload, home_meta = api_payload(
        "/football-get-standing-home", {"leagueid": LEAGUE_ID}
    )
    calls += 1
    away_payload, away_meta = api_payload(
        "/football-get-standing-away", {"leagueid": LEAGUE_ID}
    )
    calls += 1

    lks_profile = old.get("lks_profile")
    if not lks_profile or str(lks_profile.get("id")) != str(LKS_ID):
        payload, _ = api_payload("/football-league-team", {"teamid": LKS_ID})
        lks_profile = extract_profile(payload)
        calls += 1

    same_opponent = str(old.get("opponent_id")) == str(opponent_id)
    opponent_profile = old.get("opponent_profile") if same_opponent else None
    if not opponent_profile:
        payload, _ = api_payload("/football-league-team", {"teamid": opponent_id})
        opponent_profile = extract_profile(payload)
        calls += 1

    same_event = str(old.get("event_id")) == str(match.get("id"))
    h2h = old.get("h2h") if same_event else None
    if h2h is None:
        payload, _ = api_payload(
            "/football-get-head-to-head", {"eventid": match.get("id")}
        )
        h2h = extract_h2h(payload)
        calls += 1

    context = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "league_id": LEAGUE_ID,
        "event_id": match.get("id"),
        "opponent_id": opponent_id,
        "opponent_name": opponent_name,
        "lks_profile": lks_profile,
        "opponent_profile": opponent_profile,
        "home_standing": {
            "lks": get_standing(home_payload, LKS_ID),
            "opponent": get_standing(home_payload, opponent_id),
        },
        "away_standing": {
            "lks": get_standing(away_payload, LKS_ID),
            "opponent": get_standing(away_payload, opponent_id),
        },
        "h2h": h2h,
        "rapidapi_remaining": away_meta.get("remaining"),
        "requests_used_this_run": calls,
    }

    CONTEXT_FILE.write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"Zapisano data/context.json dla {opponent_name} "
        f"(teamid={opponent_id}); requesty: {calls}; "
        f"remaining: {away_meta.get('remaining')}"
    )

    build_dashboard_stats()


if __name__ == "__main__":
    main()
