#!/usr/bin/env python3

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert one-file-per-query qrels to TREC format.")
    parser.add_argument("--qrels", type=Path, required=True)
    args = parser.parse_args()

    qrel_files = sorted(args.qrels.glob("*.txt"))
    if not qrel_files:
        raise SystemExit(f"No qrels files found in {args.qrels}")

    for qrel_file in qrel_files:
        try:
            query_id = int(qrel_file.stem)
        except ValueError as error:
            raise SystemExit(f"Qrels filename must be numeric: {qrel_file}") from error

        for line_number, line in enumerate(qrel_file.read_text(encoding="utf-8").splitlines(), start=1):
            document_id = line.split("#", 1)[0].strip()
            if not document_id:
                continue
            if any(char.isspace() for char in document_id):
                raise SystemExit(f"Invalid document ID at {qrel_file}:{line_number}")
            print(f"{query_id} 0 {document_id} 1")


if __name__ == "__main__":
    main()
