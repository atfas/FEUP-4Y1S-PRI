# Search evaluation

This directory contains the evaluation pipeline for the Solr card search.
Add Solr JSON request files to `queries/` and relevance-judgment files to
`qrels/` when they are available.

## Input files

Each query file must be named with a numeric topic ID, for example
`queries/0001.json`:

```json
{
  "query": "charizard",
  "fields": "id,score",
  "limit": 10,
  "params": {
    "defType": "edismax",
    "qf": "title name rules_text pokemon__name"
  }
}
```

Each qrels file must use the same numeric topic ID, for example
`qrels/0001.txt`, with one relevant document ID per line:

```text
card:charizard-base-4
card:charizard-151-6
```

Blank lines and lines beginning with `#` are ignored.

## Running the evaluation

Start Solr and add the schema/data first:

```bash
./solr/conf/solrStart.sh
```

Run the evaluation:

```bash
make evaluate
```

The Make target automatically clones and builds `trec_eval` the first time it
is needed through `build_trec_eval.sh`. Later runs reuse the existing
executable.

The pipeline queries Solr, converts both results and qrels to TREC format, and
runs `trec_eval` with per-query metrics. Intermediate files are written to
`evaluation/output/` so results can be inspected.

Use another Solr port or core when needed:

```bash
SOLR_PORT=8984 SOLR_CORE=cards make evaluate
```
