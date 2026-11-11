#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = PROJECT_ROOT / "data" / "_solr" / "databank.json"
DEFAULT_OUT_DIR = PROJECT_ROOT / "evaluation" / "output"
DEFAULT_QRELS_DIR = PROJECT_ROOT / "evaluation" / "qrels"  # adjust to wherever your qrels live


def image_links(document):
    links = document.get("prints__image_url")
    if isinstance(links, str):
        links = [links]
    if not links:
        links = [
            print_["image_url"]
            for print_ in document.get("prints", [])
            if print_.get("image_url")
        ]
    return list(dict.fromkeys(links or []))


def query_id_arg(value: str) -> int:
    """Accept 1, 0001, etc. and return an int between 1 and 5."""
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid query {value!r}")
    if not 1 <= number <= 5:
        raise argparse.ArgumentTypeError("query must be between 0001 and 0005")
    return number


def unjudged_ids(qrels_file: Path) -> list[str]:
    """Doc IDs listed without a grade, in file order, without duplicates.

    A card that also appears with a grade elsewhere in the file counts as judged.
    """
    unjudged, judged = [], set()
    for line in qrels_file.read_text(encoding="utf-8").splitlines():
        parts = line.split("#", 1)[0].split()
        if not parts:
            continue
        if len(parts) == 1:
            unjudged.append(parts[0])
        else:
            judged.add(parts[0])
    return [doc_id for doc_id in dict.fromkeys(unjudged) if doc_id not in judged]


def main() -> None:
    parser = argparse.ArgumentParser(description="Print image links for every unjudged card in a query's qrels file.")
    parser.add_argument("--query", "-q", type=query_id_arg, required=True, help="query to review: 0001 to 0005 (1 to 5 also works)")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--qrels-dir", type=Path, default=DEFAULT_QRELS_DIR)
    args = parser.parse_args()

    qrels_file = args.qrels_dir / f"{args.query:04d}.txt"
    if not qrels_file.exists():
        raise SystemExit(f"No qrels file found at {qrels_file}")

    todo = unjudged_ids(qrels_file)
    if not todo:
        print(f"Query {args.query:04d}: no unjudged cards.")
        return

    documents = {
        doc["id"]: doc
        for doc in json.loads(args.data.read_text(encoding="utf-8"))
        if "id" in doc
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Query {args.query:04d}: {len(todo)} unjudged cards\n")
    missing = []
    for card_id in todo:
        document = documents.get(card_id)
        if document is None:
            missing.append(card_id)
            continue

        filename = re.sub(r"[^0-9A-Za-z_-]", "_", card_id) + ".json"
        out_path = args.out_dir / filename
        out_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        print(card_id)
        links = image_links(document)
        if links:
            for link in links:
                print(f"  {link}")
        else:
            print("  No image links found.")
        print()

    if missing:
        print(f"Not found in {args.data.name} ({len(missing)}):")
        for card_id in missing:
            print(f"  {card_id}")


if __name__ == "__main__":
    main()