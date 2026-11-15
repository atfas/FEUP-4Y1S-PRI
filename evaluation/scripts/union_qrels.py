#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QRELS_DIR = PROJECT_ROOT / "evaluation" / "qrels"


@dataclass
class Entry:
    document_id: str
    grade: int | None
    line: str


def qrel_files(qrels_dir: Path) -> list[Path]:
    return sorted(
        qrels_dir.glob("*.txt"),
        key=lambda path: (not path.stem.isdigit(), int(path.stem) if path.stem.isdigit() else path.stem),
    )


def read_qrels(path: Path) -> tuple[list[str], dict[str, Entry]]:
    header = []
    entries: dict[str, Entry] = {}
    seen_entry = False

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        fields = line.split("#", 1)[0].split()
        if not fields:
            if not seen_entry:
                header.append(line)
            continue
        if len(fields) > 2:
            raise SystemExit(f"Invalid line at {path}:{line_number}: {line!r}")

        seen_entry = True
        document_id = fields[0]
        grade = None
        if len(fields) == 2:
            try:
                grade = int(fields[1])
            except ValueError as error:
                raise SystemExit(f"Grade must be an integer at {path}:{line_number}") from error
            if grade < 0:
                raise SystemExit(f"Grade must be >= 0 at {path}:{line_number}")

        previous = entries.get(document_id)
        if previous is not None:
            if previous.grade is not None and grade is not None and previous.grade != grade:
                raise SystemExit(
                    f"Conflicting grades for {document_id} in {path}: "
                    f"{previous.grade} and {grade}"
                )
            if previous.grade is None and grade is not None:
                entries[document_id] = Entry(document_id, grade, line)
        else:
            entries[document_id] = Entry(document_id, grade, line)

    return header, entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add the union of all qrels entries to every qrels file as unjudged where missing."
    )
    parser.add_argument("--qrels-dir", type=Path, default=DEFAULT_QRELS_DIR)
    args = parser.parse_args()

    files = qrel_files(args.qrels_dir)
    if not files:
        raise SystemExit(f"No qrels files found in {args.qrels_dir}")

    parsed = {path: read_qrels(path) for path in files}
    union = list(dict.fromkeys(
        document_id
        for path in files
        for document_id in parsed[path][1]
    ))

    total_added = 0
    total_removed = 0
    for path in files:
        header, entries = parsed[path]
        missing = [document_id for document_id in union if document_id not in entries]
        total_added += len(missing)
        total_removed += sum(
            1
            for line in path.read_text(encoding="utf-8").splitlines()
            if (fields := line.split("#", 1)[0].split())
            and fields[0] in entries
        ) - len(entries)

        output = [
            *header,
            *(
                entries[document_id].line if document_id in entries else document_id
                for document_id in sorted(union)
            ),
        ]
        new_text = "\n".join(output) + "\n"
        if path.read_text(encoding="utf-8") != new_text:
            path.write_text(new_text, encoding="utf-8")

    print(
        f"Union contains {len(union)} unique cards; added {total_added} unjudged "
        f"entries and removed {total_removed} duplicate entries across {len(files)} qrels files."
    )


if __name__ == "__main__":
    main()
