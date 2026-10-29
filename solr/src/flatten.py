"""Flatten the search-ready documents for Solr.

    python -m solr.src.flatten data/_collections/cards.json data/_collections/pokemon.json \
        data/_collections/artists.json data/_collections/expansions.json \
        --out-dir data/_solr --schema

Each file becomes data/_solr/<name>.json (a JSON array, which Solr's /update handler accepts).

How a document is flattened (recursively, innermost first)
----------------------------------------------------------
* A dict: each child key is prefixed with its parent's key, joined by "_":
      {"infobox": {"hp": 50}}                  ->  {"infobox_hp": 50}
* A list of dicts: every item is flattened first, then the items' fields with the same name are
  concatenated into one list (a multiValued field in Solr):
      {"prints": [{"rarity": "Common", "prices": [{"market": 1}, {"market": 2}]},
                  {"rarity": "Rare",   "prices": [{"market": 9}]}]}
      ->  {"prints_rarity": ["Common", "Rare"], "prints_prices_market": [1, 2, 9]}
* A list of plain values stays a list.
* Nulls, empty strings, empty lists and empty dicts are dropped (Solr cannot index a null).
* Timestamps such as 2026-10-11T20:05:45+0000 become Solr dates (2026-10-11T20:05:45Z).

What flattening loses
---------------------
The position of a value inside its list. "prints_rarity" and "prints_card_number" are separate lists,
so a query for "rarity Common AND number 63" can match two different prints, and a price cannot be
tied to the rarity of its own print. If you need per-print queries, index each print as its own
document or as a Solr child document instead.

Solr needs a field to be multiValued consistently, so any field that comes from a list is always
written as a list, even for a document where the list has one item.
Standard library only.
"""
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SEPARATOR = "_"
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?$")
SOLR_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
BIG_INT = 2 ** 31 - 1  # larger integers need Solr's plong instead of pint
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "_solr"


# ---------- values ----------
def solr_date(text):
    """'2026-10-11T20:05:45+0000' -> '2026-10-11T20:05:45Z' (in UTC), or None if it is not a timestamp."""
    if not TIMESTAMP.match(text):
        return None
    cleaned = text.replace("Z", "+0000")
    cleaned = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", cleaned)  # +00:00 -> +0000
    if not re.search(r"[+-]\d{4}$", cleaned):
        cleaned += "+0000"  # no offset given: assume UTC
    pattern = "%Y-%m-%dT%H:%M:%S.%f%z" if "." in cleaned else "%Y-%m-%dT%H:%M:%S%z"
    try:
        moment = datetime.strptime(cleaned, pattern)
    except ValueError:
        return None
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_key(key):
    """Field names Solr is happy with: letters, digits and underscores."""
    return re.sub(r"[^0-9A-Za-z_]", "_", str(key))


# ---------- the recursive flatten ----------
def flatten(value, sep=SEPARATOR):
    """Flatten one value.

    Returns a dict of {field name: value or list of values} for dicts and lists of dicts,
    a list for a list of plain values, a plain value for scalars, and None for anything empty.
    """
    if isinstance(value, dict):
        fields = {}
        for key, child in value.items():
            flat = flatten(child, sep)
            if isinstance(flat, dict):
                named = {f"{safe_key(key)}{sep}{inner}": v for inner, v in flat.items()}
            elif flat is None:
                continue
            else:
                named = {safe_key(key): flat}
            for name, v in named.items():
                if name in fields:
                    raise ValueError(f"two fields flatten to the same name: {name!r}")
                fields[name] = v
        return fields

    if isinstance(value, list):
        merged, scalars = {}, []
        for item in value:
            flat = flatten(item, sep)
            if isinstance(flat, dict):  # an item that was a dict: concatenate its fields across items
                for name, v in flat.items():
                    merged.setdefault(name, []).extend(v if isinstance(v, list) else [v])
            elif isinstance(flat, list):
                scalars.extend(flat)
            elif flat is not None:
                scalars.append(flat)
        if merged:
            if scalars:  # a list mixing dicts and plain values: keep the plain ones under "value"
                merged.setdefault("value", []).extend(scalars)
            return merged
        return scalars or None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        return solr_date(value) or value
    return value  # numbers and booleans (None stays None)


def flatten_documents(documents, sep=SEPARATOR):
    """Flatten every document and make the multi-valued fields consistent.

    Returns (flat documents, set of multi-valued field names).
    """
    flat_docs = [flatten(document, sep) or {} for document in documents]
    multivalued = {name for doc in flat_docs for name, v in doc.items() if isinstance(v, list)}
    for doc in flat_docs:
        for name in multivalued:
            if name in doc and not isinstance(doc[name], list):
                doc[name] = [doc[name]]
    return flat_docs, multivalued


# ---------- describing the fields (types for the Solr schema) ----------
def value_type(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str) and SOLR_DATE.match(value):
        return "date"
    return "string"


def describe_fields(flat_docs, multivalued):
    fields = {}
    for doc in flat_docs:
        for name, value in doc.items():
            info = fields.setdefault(name, {"types": Counter(), "docs": 0, "max_length": 0, "words": 0,
                                            "strings": 0, "max_int": 0, "example": None})
            info["docs"] += 1
            for item in value if isinstance(value, list) else [value]:
                kind = value_type(item)
                info["types"][kind] += 1
                if kind == "string":
                    info["max_length"] = max(info["max_length"], len(item))
                    info["words"] += len(item.split())
                    info["strings"] += 1
                if kind == "int":
                    info["max_int"] = max(info["max_int"], abs(item))
                if info["example"] is None:
                    info["example"] = item
    for name, info in fields.items():
        info["multiValued"] = name in multivalued
        info["solr_type"] = solr_type(info)
    return fields


def solr_type(info):
    kinds = set(info["types"])
    if kinds == {"bool"}:
        return "boolean"
    if kinds == {"date"}:
        return "pdate"
    if kinds == {"int"}:
        return "plong" if info["max_int"] > BIG_INT else "pint"
    if kinds <= {"int", "float"}:
        return "pdouble"
    # strings (also the fallback for mixed types): long or wordy values are searchable text
    average_words = info["words"] / info["strings"] if info["strings"] else 0
    return "text_general" if info["max_length"] > 100 or average_words > 3 else "string"


def schema_payload(fields):
    """Solr Schema API commands: POST this to /solr/<core>/schema to define the fields."""
    commands = []
    for name, info in sorted(fields.items()):
        if name == "id":  # the unique key already exists in the default schema
            continue
        commands.append({"name": name, "type": info["solr_type"],
                         "multiValued": info["multiValued"], "stored": True, "indexed": True})
    return {"add-field": commands}


# ---------- command line ----------
def process_file(path, out_dir, sep, write_schema, lines):
    documents = json.loads(Path(path).read_text(encoding="utf-8"))
    flat_docs, multivalued = flatten_documents(documents, sep)
    fields = describe_fields(flat_docs, multivalued)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / Path(path).name
    if lines:
        text = "\n".join(json.dumps(doc, ensure_ascii=False) for doc in flat_docs) + "\n"
    else:
        text = json.dumps(flat_docs, ensure_ascii=False)
    out_path.write_text(text, encoding="utf-8")

    mixed = {n: dict(i["types"]) for n, i in fields.items() if len(i["types"]) > 1}
    print(f"{path}: {len(flat_docs):,} documents, {len(fields)} fields "
          f"({len(multivalued)} multi-valued) -> {out_path}")
    if "id" not in fields:
        print("  WARNING: no 'id' field; Solr needs a unique key")
    if mixed:
        print(f"  mixed value types (Solr will reject these in one field): {mixed}")

    if write_schema:
        schema_path = out_dir / f"{Path(path).stem}_schema.json"
        schema_path.write_text(json.dumps(schema_payload(fields), indent=2), encoding="utf-8")
        print(f"  schema commands -> {schema_path}")
    return flat_docs, fields


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+", help="search-ready json files (each a list of documents)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    parser.add_argument("--sep", default=SEPARATOR, help='joins parent and child names (default "_")')
    parser.add_argument("--schema", action="store_true", help="also write <name>_schema.json (Schema API commands)")
    parser.add_argument("--lines", action="store_true", help="write one document per line instead of a JSON array")
    args = parser.parse_args()
    for path in args.files:
        process_file(path, args.out_dir, args.sep, args.schema, args.lines)


if __name__ == "__main__":
    main()