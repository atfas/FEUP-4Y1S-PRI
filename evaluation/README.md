# Search evaluation

This directory contains the evaluation pipeline for the Solr card search:
queries in `queries/`, relevance judgments (qrels) in `qrels/`, helper scripts in
`scripts/` and generated results in `output/`.

## Directory layout

```text
evaluation/
├── queries/            # one JSON Solr request per topic: 0001.json, 0002.json, ...
├── qrels/              # one relevance file per topic: 0001.txt, 0002.txt, ...
├── scripts/
│   ├── query_solr.py   # run every query against Solr
│   ├── solr2trec.py    # Solr JSON responses -> TREC run format
│   ├── qrels2trec.py   # qrels files -> TREC qrels (skips unjudged entries)
│   ├── update_qrels.py # add retrieved-but-unjudged docs to a qrels file
│   └── export_card.py  # print image links for every unjudged card
├── build_trec_eval.sh  # clone and build trec_eval
└── output/             # generated: qrels.trec, results.trec, metrics.txt, card JSON
```

## Input files

### Queries

Each query file must be named with a numeric topic ID, for example
`queries/0001.json`:

```json
{
  "query": "attacks discard pile",
  "fields": "id,score",
  "limit": 30,
  "sort": "score desc,id asc",
  "params": {
    "defType": "edismax",
    "qf": "effect_all^5.0 card_text__attackeffect^3.0 rules_text^1.0",
    "debugQuery": "true"
  }
}
```

The file is sent as-is to the Solr `select` endpoint, so `query`, `fields`,
`limit`, `sort` and `params` follow the normal Solr JSON request API. A new
query is added by copying an existing file and changing the `query`/`params`.

### Qrels

Each qrels file uses the same numeric topic ID, for example `qrels/0001.txt`.
Every non-empty line is a document ID optionally followed by a grade:

```text
# comment lines are ignored
card:charizard-base-4 1      # relevant
card:charizard-151-6 0       # not relevant
card:charizard-ex-generations-11
```

- `1` marks the card as relevant, `0` as not relevant.
- A line with only a document ID (no grade) is an *unjudged placeholder*. It is
  skipped when the TREC qrels are built, so it does not affect the metrics.
- Only one grade per document is allowed; conflicting grades abort the run.
- A qrels file needs at least one graded entry (`0` or `1`). If every line is
  unjudged, that query is skipped by `qrels2trec.py`.

## Running the evaluation

Index the corpus and start Solr first:

```bash
make flatten                 # data/_collections -> data/_solr (needed by Solr)
./solr/conf/solrStart.sh     # start container, apply schema, index data
```

Then run every query and compute metrics:

```bash
make evaluate
```

This target builds `trec_eval` the first time (via `build_trec_eval.sh`) and
then runs `evaluate.sh`, which:

1. converts all `qrels/*.txt` to `output/qrels.trec` (`qrels2trec.py`);
2. runs every `queries/*.json` against Solr (`query_solr.py`);
3. converts the responses to `output/results.trec` (`solr2trec.py`);
4. runs `trec_eval` and writes per-query metrics to `output/metrics.txt`.

Use another Solr port or core when needed:

```bash
SOLR_PORT=8984 SOLR_CORE=cards make evaluate
```

## Judging results (`make post-eval`)

`make post-eval` is the interactive loop used to turn retrieved documents into
judgments. It runs `make evaluate` first (so Solr must be running), then:

1. `update_qrels.py` reads `output/results.trec` and appends every document
   retrieved for the topic but missing from `qrels/<topic>.txt` as an unjudged
   placeholder (document ID only).
2. `export_card.py` reads the qrels file, loads the matching documents from
   `data/_solr/databank.json`, saves each one to `output/<document_id>.json`,
   and prints the document ID followed by its card image link(s). Each run
   clears the card JSON files exported by previous runs first, so `output/`
   only contains the batch currently under review.

```bash
make post-eval QUERY=0001
```

For every link printed, open the image and decide whether the card is relevant
to the query, then edit `qrels/<topic>.txt` and add the grade after the ID:

```text
card:some-card-1-1 1    # relevant
card:some-card-2-2 0    # not relevant
```

After judging a batch, rerun `make evaluate` (or `make post-eval QUERY=...`
again) to refresh the metrics and pull the next batch of unjudged results.
Cards saved to `output/<document_id>.json` can be inspected without querying
Solr again, which is handy for images in Japanese or other languages where the
card text needs a closer look.

> `post-eval` currently accepts topics `0001` to `0005` (the scripts enforce
> that range). `QUERY=1` and `QUERY=0001` are equivalent.

## Adding a new query

1. Add `queries/NNNN.json` with the same structure as the existing files and the
   Solr parameters to test, using the next free numeric ID.
2. Add `qrels/NNNN.txt` containing at least one **graded** placeholder, either
   relevant or not relevant, for example:

   ```text
   card:charizard-base-4 1
   ```

   Do not leave it empty or with only ungraded IDs: unjudged entries are
   skipped, and the query needs at least one judgment to be evaluated.
3. Make sure Solr is running, then bootstrap the topic:

   ```bash
   make post-eval QUERY=NNNN
   ```

   This retrieves the results, appends them to `qrels/NNNN.txt` as unjudged
   placeholders, and prints the image links to review. Grade the cards as
   described above and rerun `make evaluate` when done.

The search parameters can be tuned by editing `queries/NNNN.json` and rerunning
`make post-eval QUERY=NNNN`; the qrels file is reused, so already judged cards
keep their grades.
