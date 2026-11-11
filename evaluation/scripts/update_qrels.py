#!/usr/bin/env python3

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QRELS_DIR = PROJECT_ROOT / "evaluation" / "qrels"  # adjust to wherever your qrels live


def query_id_arg(value: str) -> int:
    """Accept 1, 0001, etc. and return an int between 1 and 5."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid query {value!r}")
    if not 1 <= number <= 5:
        raise argparse.ArgumentTypeError("query must be between 0001 and 0005")
    return number


def load_results(results_file: Path, query_number: int) -> list[str]:
    """Return the doc IDs retrieved for one query, in rank order, without duplicates.

    Assumes TREC run format: query_id Q0 doc_id rank score tag
    Swap this function out if your results come in a different format.
    """
    doc_ids = []
    for line in results_file.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            if int(parts[0]) != query_number:
                continue
        except ValueError:
            continue
        doc_ids.append(parts[2])
    return list(dict.fromkeys(doc_ids))


def existing_ids(qrels_file: Path) -> set[str]:
    """Doc IDs already in a qrels file, whether judged or not."""
    if not qrels_file.exists():
        return set()
    ids = set()
    for line in qrels_file.read_text(encoding="utf-8").splitlines():
        parts = line.split("#", 1)[0].split()
        if parts:
            ids.add(parts[0])
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Add any retrieved docs missing from a query's qrels file, as unjudged.")
    parser.add_argument("--results", type=Path, required=True, help="TREC-format run file with the search results")
    parser.add_argument("--query", "-q", type=query_id_arg, required=True, help="query to sync: 0001 to 0005 (1 to 5 also works)")
    parser.add_argument("--qrels-dir", type=Path, default=DEFAULT_QRELS_DIR)
    args = parser.parse_args()

    results = load_results(args.results, args.query)
    if not results:
        raise SystemExit(f"No results found for query {args.query} in {args.results}")

    args.qrels_dir.mkdir(parents=True, exist_ok=True)
    qrels_file = args.qrels_dir / f"{args.query:04d}.txt"

    present = existing_ids(qrels_file)
    missing = [doc_id for doc_id in results if doc_id not in present]

    if missing:
        text = qrels_file.read_text(encoding="utf-8") if qrels_file.exists() else ""
        prefix = "" if not text or text.endswith("\n") else "\n"
        with qrels_file.open("a", encoding="utf-8") as f:
            f.write(prefix + "".join(f"{doc_id}\n" for doc_id in missing))

    print(f"Query {args.query:04d}: {len(results)} results, {len(results) - len(missing)} already in qrels, {len(missing)} added as unjudged -> {qrels_file}")
    for doc_id in missing:
        print(f"  + {doc_id}")


if __name__ == "__main__":
    main()