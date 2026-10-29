# Solr phase

Phase 2 indexes the merged corpus from `data/collection/databank.json` in Solr.

The first step is `solr/src/flatten.py`, which flattens nested documents and can emit
Schema API commands:

```bash
make flatten
# or
uv run python -m solr.src.flatten data/collection/databank.json \
    --out-dir data/collection/solr --schema
```

Generated files live in `data/collection/solr/` and are not committed.
