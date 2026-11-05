#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Run numbered JSON queries against Solr.")
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--uri", default="http://localhost:8983/solr")
    parser.add_argument("--collection", default="cards")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()

    query_files = sorted(args.queries.glob("*.json"))
    if not query_files:
        raise SystemExit(f"No query JSON files found in {args.queries}")

    results = {}
    for query_file in query_files:
        try:
            query_id = int(query_file.stem)
        except ValueError as error:
            raise SystemExit(f"Query filename must be numeric: {query_file}") from error

        try:
            query = json.loads(query_file.read_text(encoding="utf-8"))
            response = requests.post(
                f"{args.uri.rstrip('/')}/{args.collection}/select",
                json=query,
                timeout=args.timeout,
            )
            response.raise_for_status()
            results[str(query_id)] = response.json()
        except (OSError, json.JSONDecodeError, requests.RequestException) as error:
            raise SystemExit(f"Could not process {query_file}: {error}") from error

    json.dump(results, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
