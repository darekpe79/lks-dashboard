import argparse
import json
import re
from datetime import datetime, timedelta, timezone

from api_client import REPO_ROOT, call_api
from build_dashboard_stats import main as build_dashboard_stats

LKS_ID = 8244
LEAGUE_ID = 197
OPPONENT_FORM_MAX_AGE_DAYS = 3

SEASON_FILE = REPO_ROOT / "data" / "lks_current_season.json"
CONTEXT_FILE = REPO_ROOT / "data" / "context.json"


def now_utc():
    return datetime.now(timezone.utc)


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


def normalize_standings(payload):
    rows = payload.get("response", {}).get("standing", [])
    return [
        {
            "position": row.get("idx"),
            "id": row.get("id"),
            "name": row.get("name"),
            "played": row.get("played"),
            "wins": row.get("wins"),
            "draws": row.get("draws"),
            "losses": row.get("losses"),
            "goals": row.get("scoresStr"),
            "goal_difference": row.get("goalConDiff"),
            "points": row.get("pts"),
            "qualColor": row.get("qualColor"),
        }
        for row in rows
    ]


def get_team_row(rows, team_id):
    return next(
        (row for row in rows if str(row.get("id")) == str(team_id)),
        None,
    )


def result_for_team(match, team_id):
    is_home = str(match.get("homeTeamId")) == str(team_id)
    gf = match.get("homeTeamScore") if is_home else match.get("awayTeamScore")
    ga = match.get("awayTeamScore") if is_home else match.get("homeTeamScore")
    if gf is None or ga is None:
        return None
    if gf > ga:
        return "W"
    if gf < ga:
        return "L"
    return "D"


def extract_opponent_form(payload, team_id, season_start):
    suggestions = payload.get("response", {}).get("suggestions", [])
    matches = [
        match for match in suggestions
        if isinstance(match, dict)
        and match.get("type") == "match"
        and str(match.get("leagueId")) == str(LEAGUE_ID)
        and (match.get("matchDate") or "") >= season_start
        and (match.get("status") or {}).get("finished") is True
        and (
            str(match.get("homeTeamId")) == str(team_id)
            or str(match.get("awayTeamId")) == str(team_id)
        )
    ]

    dedup = {}
    for match in matches:
        event_id = match.get("id")
        if event_id is not None:
            dedup[str(event_id)] = match

    matches = sorted(
        dedup.values(),
        key=lambda match: match.get("matchDate") or "",
    )[-5:]

    form = []
    for match in matches:
        is_home = str(match.get("homeTeamId")) == str(team_id)
        opponent_id = match.get("awayTeamId") if is_home else match.get("homeTeamId")
        opponent_name = (
            match.get("awayTeamName") if is_home else match.get("homeTeamName")
        )
        gf = match.get("homeTeamScore") if is_home else match.get("awayTeamScore")
        ga = match.get("awayTeamScore") if is_home else match.get("homeTeamScore")
        result = result_for_team(match, team_id)
        if result is None:
            continue

        form.append({
            "event_id": match.get("id"),
            "date": match.get("matchDate"),
            "result": result,
            "opponent_id": opponent_id,
            "opponent": opponent_name,
            "venue": "home" if is_home else "away",
            "score_for": gf,
            "score_against": ga,
            "score": f"{gf}:{ga}",
        })

    return form


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


def older_than_days(value, days):
    if not value:
        return True
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    return now_utc() - dt >= timedelta(days=days)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("auto", "weekly"),
        default="auto",
        help=(
            "auto: użyj API tylko po zmianie najbliższego meczu/rywala; "
            "weekly: dodatkowo odśwież home/away, jeśli mają co najmniej 5 dni."
        ),
    )
    args = parser.parse_args()

    match, opponent_id, opponent_name = get_next_opponent()
    season_doc = json.loads(SEASON_FILE.read_text(encoding="utf-8"))
    season_start = season_doc.get("season_start", "2026-07-01T00:00:00Z")

    old = {}
    if CONTEXT_FILE.exists():
        old = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))

    same_opponent = str(old.get("opponent_id")) == str(opponent_id)
    same_event = str(old.get("event_id")) == str(match.get("id"))

    need_lks_profile = not old.get("lks_profile")
    need_opponent_profile = (not same_opponent) or not old.get("opponent_profile")
    need_h2h = (not same_event) or old.get("h2h") is None
    need_opponent_form = (
        not same_opponent
        or older_than_days(
            old.get("opponent_form_updated_at_utc"),
            OPPONENT_FORM_MAX_AGE_DAYS,
        )
    )

    need_home_away = (
        not old.get("home_standing")
        or not old.get("away_standing")
        or not same_opponent
        or (
            args.mode == "weekly"
            and older_than_days(old.get("home_away_updated_at_utc"), 5)
        )
    )

    if not any((
        need_lks_profile,
        need_opponent_profile,
        need_h2h,
        need_home_away,
        need_opponent_form,
    )):
        if old.get("opponent_name") != opponent_name:
            old["opponent_name"] = opponent_name
            CONTEXT_FILE.write_text(
                json.dumps(old, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            build_dashboard_stats()
        print("Context aktualny — 0 requestów do RapidAPI.")
        return

    calls = 0
    last_meta = None

    if need_home_away:
        home_payload, last_meta = api_payload(
            "/football-get-standing-home", {"leagueid": LEAGUE_ID}
        )
        calls += 1
        away_payload, last_meta = api_payload(
            "/football-get-standing-away", {"leagueid": LEAGUE_ID}
        )
        calls += 1
        home_table = normalize_standings(home_payload)
        away_table = normalize_standings(away_payload)
        home_standing = {
            "lks": get_team_row(home_table, LKS_ID),
            "opponent": get_team_row(home_table, opponent_id),
        }
        away_standing = {
            "lks": get_team_row(away_table, LKS_ID),
            "opponent": get_team_row(away_table, opponent_id),
        }
        home_away_updated_at_utc = now_utc().isoformat()
    else:
        home_standing = old.get("home_standing")
        away_standing = old.get("away_standing")
        home_table = old.get("home_table", [])
        away_table = old.get("away_table", [])
        home_away_updated_at_utc = old.get("home_away_updated_at_utc")

    lks_profile = old.get("lks_profile")
    if need_lks_profile:
        payload, last_meta = api_payload("/football-league-team", {"teamid": LKS_ID})
        lks_profile = extract_profile(payload)
        calls += 1

    opponent_profile = old.get("opponent_profile") if same_opponent else None
    if need_opponent_profile:
        payload, last_meta = api_payload(
            "/football-league-team", {"teamid": opponent_id}
        )
        opponent_profile = extract_profile(payload)
        calls += 1

    h2h = old.get("h2h") if same_event else None
    if need_h2h:
        payload, last_meta = api_payload(
            "/football-get-head-to-head", {"eventid": match.get("id")}
        )
        h2h = extract_h2h(payload)
        calls += 1

    opponent_form = old.get("opponent_form", []) if same_opponent else []
    opponent_form_updated_at_utc = (
        old.get("opponent_form_updated_at_utc") if same_opponent else None
    )
    opponent_form_search = old.get("opponent_form_search") if same_opponent else None

    if need_opponent_form:
        # Search jest tylko etapem discovery. Każdy wynik jest potem
        # rygorystycznie filtrowany po teamId, leagueId, sezonie i statusie.
        calls += 1
        try:
            payload, last_meta = api_payload(
                "/football-matches-search", {"search": opponent_name}
            )
            opponent_form = extract_opponent_form(
                payload,
                opponent_id,
                season_start,
            )
            opponent_form_search = opponent_name
            print(
                f"Forma {opponent_name}: {len(opponent_form)} poprawnych "
                "meczów po filtrze ID."
            )
        except Exception as exc:
            # Forma przeciwnika jest dodatkiem: jej błąd nie może
            # zatrzymać aktualizacji całego dashboardu.
            print(
                f"OSTRZEŻENIE: nie udało się odświeżyć formy "
                f"{opponent_name}: {exc}"
            )
        finally:
            # Nawet po błędzie nie ponawiamy requestu przy każdym runie.
            opponent_form_updated_at_utc = now_utc().isoformat()

    context = {
        "updated_at_utc": now_utc().isoformat(),
        "home_away_updated_at_utc": home_away_updated_at_utc,
        "league_id": LEAGUE_ID,
        "event_id": match.get("id"),
        "opponent_id": opponent_id,
        "opponent_name": opponent_name,
        "lks_profile": lks_profile,
        "opponent_profile": opponent_profile,
        "home_standing": home_standing,
        "away_standing": away_standing,
        "home_table": home_table,
        "away_table": away_table,
        "h2h": h2h,
        "opponent_form": opponent_form,
        "opponent_form_updated_at_utc": opponent_form_updated_at_utc,
        "opponent_form_search": opponent_form_search,
        "rapidapi_remaining": (
            last_meta.get("remaining") if last_meta else old.get("rapidapi_remaining")
        ),
        "requests_used_this_run": calls,
    }

    CONTEXT_FILE.write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        f"Zapisano data/context.json dla {opponent_name} "
        f"(teamid={opponent_id}); requesty: {calls}; "
        f"remaining: {context.get('rapidapi_remaining')}"
    )

    build_dashboard_stats()


if __name__ == "__main__":
    main()
