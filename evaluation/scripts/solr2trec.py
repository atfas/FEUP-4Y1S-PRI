#!/usr/bin/env python3

import argparse
import json
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Solr JSON responses to TREC run format.")
    parser.add_argument("--run-id", default="cards_solr")
    args = parser.parse_args()

    responses = json.load(sys.stdin)
    for query_id, response in sorted(responses.items(), key=lambda item: int(item[0])):
        try:
            documents = response["response"]["docs"]
        except KeyError as error:
            raise SystemExit(f"Invalid Solr response for query {query_id}: missing response.docs") from error

        for rank, document in enumerate(documents, start=1):
            try:
                document_id = document["id"]
                score = document.get("score", 0)
            except KeyError as error:
                raise SystemExit(f"Solr result for query {query_id} has no id") from error
            print(f"{int(query_id)} Q0 {document_id} {rank} {score} {args.run_id}")


if __name__ == "__main__":
    main()
