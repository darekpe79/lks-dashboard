import argparse
import json
import re
from pathlib import Path

from api_client import REPO_ROOT, call_api


def parse_params(items):
    params = {}
    for item in items:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"Parametr musi mieć postać klucz=wartość: {item}"
            )
        key, value = item.split("=", 1)
        params[key] = value
    return params


def safe_name(endpoint):
    name = endpoint.strip("/").replace("/", "_")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name) or "response"


parser = argparse.ArgumentParser(
    description="Jednorazowy tester endpointów Free API Live Football Data."
)
parser.add_argument(
    "endpoint",
    help="Ścieżka endpointu, np. /football-current-live",
)
parser.add_argument(
    "--param",
    action="append",
    default=[],
    metavar="KEY=VALUE",
    help="Query parameter; można podać wielokrotnie.",
)
parser.add_argument(
    "--output",
    help="Ścieżka pliku JSON. Domyślnie api_tests/<endpoint>.json",
)
args = parser.parse_args()

params = parse_params(args.param)
output = args.output or f"api_tests/{safe_name(args.endpoint)}.json"

print("UWAGA: to uruchomienie wykona dokładnie 1 request do RapidAPI.")
print(f"Endpoint: {args.endpoint}")
print(f"Params: {params}")

result = call_api(args.endpoint, params=params, save_to=output)
meta = result["meta"]

print(f"HTTP: {meta['status_code']}")
print(f"RapidAPI remaining: {meta['remaining']} / {meta['limit']}")
print(f"Zapisano: {Path(output)}")
print("Podgląd odpowiedzi:")
print(json.dumps(result["data"], ensure_ascii=False, indent=2)[:2500])
