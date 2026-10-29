# Solr phase

Phase 2 indexes the merged corpus from `data/_collections/databank.json` in Solr.

The first step is `solr/src/flatten.py`, which flattens nested documents and can emit
Schema API commands:

```bash
make flatten
# or
uv run python -m solr.src.flatten data/_collections/databank.json \
    --out-dir data/_solr --sep __ --schema
```

Generated files live in `data/_solr/` and are not committed.
