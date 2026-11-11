#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert one-file-per-query qrels to TREC format.")
    parser.add_argument("--qrels", type=Path, required=True)
    args = parser.parse_args()

    qrel_files = sorted(args.qrels.glob("*.txt"), key=lambda p: (not p.stem.isdigit(), int(p.stem) if p.stem.isdigit() else 0))
    if not qrel_files:
        raise SystemExit(f"No qrels files found in {args.qrels}")

    unjudged = 0
    for qrel_file in qrel_files:
        try:
            query_id = int(qrel_file.stem)
        except ValueError as error:
            raise SystemExit(f"Qrels filename must be numeric: {qrel_file}") from error

        grades: dict[str, int] = {}
        for line_number, line in enumerate(qrel_file.read_text(encoding="utf-8").splitlines(), start=1):
            parts = line.split("#", 1)[0].split()
            if not parts:
                continue
            if len(parts) == 1:
                unjudged += 1  # listed but not yet analysed
                continue
            if len(parts) > 2:
                raise SystemExit(f"Invalid line at {qrel_file}:{line_number}: {line!r}")

            document_id, raw_grade = parts
            try:
                grade = int(raw_grade)
            except ValueError as error:
                raise SystemExit(f"Grade must be an integer at {qrel_file}:{line_number}") from error
            if grade < 0:
                raise SystemExit(f"Grade must be >= 0 at {qrel_file}:{line_number}")
            if document_id in grades and grades[document_id] != grade:
                raise SystemExit(f"Conflicting grades for {document_id} at {qrel_file}:{line_number}")
            grades[document_id] = grade

        for document_id, grade in grades.items():
            print(f"{query_id} 0 {document_id} {grade}")

    if unjudged:
        print(f"Skipped {unjudged} unjudged entries (no grade column)", file=sys.stderr)


if __name__ == "__main__":
    main()