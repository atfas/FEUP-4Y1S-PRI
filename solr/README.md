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

## Search systems

Start Solr and index the corpus once:

```bash
./solr/conf/solrStart.sh
```

Then choose or switch the search system independently:

```bash
./solr/conf/solrSetDefault.sh   # standard Lucene parser
./solr/conf/solrSetAdvanced.sh  # eDisMax with field and phrase boosts
```

Both settings update the `/select` handler, so the evaluation queries work unchanged in either
system. Starting Solr recreates the core and resets its configuration; select a system afterward
for manual searches.

The advanced system searches the combined `effect_all` field and gives additional weight to
attack effects, ability effects and rules text. Phrase matches are boosted, and `mm` lets a
limited number of terms be absent while requiring most terms in longer queries. To query the
active system:

```bash
curl --get 'http://localhost:8983/solr/cards/select' \
    --data-urlencode 'q=discard pile'
```

Parser selection and system-wide weights live in `solr/conf/default-system.json` and
`solr/conf/advanced-system.json`, not in individual query files. Query-specific filters can remain
in a query's `params`.

For evaluation, run `make evaluate SYSTEM=default` or `make evaluate SYSTEM=advanced`.
Evaluation selects and leaves active the requested system; results are stored separately under
`evaluation/output/`.
See [evaluation/README.md](../evaluation/README.md) for the judging workflow.
