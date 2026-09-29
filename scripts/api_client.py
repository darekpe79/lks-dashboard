import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HOST = "free-api-live-football-data.p.rapidapi.com"
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_local_env():
    """Load .env locally. Existing environment variables (e.g. GitHub Secrets) win."""
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def get_api_key():
    load_local_env()
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        raise RuntimeError(
            "Brak RAPIDAPI_KEY. Lokalnie dodaj go do .env; "
            "w GitHub Actions używamy repozytoryjnego Secret RAPIDAPI_KEY."
        )
    return api_key


def call_api(endpoint, params=None, save_to=None, timeout=30):
    """Perform exactly one GET request to RapidAPI."""
    api_key = get_api_key()
    params = params or {}

    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    query = urlencode(params)
    url = f"https://{HOST}{endpoint}"
    if query:
        url += f"?{query}"

    request = Request(
        url,
        headers={
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": HOST,
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            raw = response.read().decode("utf-8")
            headers = response.headers
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"RapidAPI zwróciło HTTP {exc.code}: {body[:1000]}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Błąd połączenia z RapidAPI: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw_text": raw}

    result = {
        "meta": {
            "endpoint": endpoint,
            "params": params,
            "status_code": status,
            "limit": headers.get("x-ratelimit-requests-limit"),
            "remaining": headers.get("x-ratelimit-requests-remaining"),
            "reset": headers.get("x-ratelimit-requests-reset"),
            "content_type": headers.get("content-type"),
        },
        "data": data,
    }

    if save_to is not None:
        path = Path(save_to)
        if not path.is_absolute():
            path = REPO_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return result
