#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
EVALUATION_DIR="${PROJECT_ROOT}/evaluation"
QUERIES_DIR="${EVALUATION_DIR}/queries"
QRELS_DIR="${EVALUATION_DIR}/qrels"
OUTPUT_DIR="${EVALUATION_DIR}/output"
TREC_EVAL_BIN="${TREC_EVAL_BIN:-${EVALUATION_DIR}/trec_eval/trec_eval}"
SOLR_PORT="${SOLR_PORT:-8983}"
SOLR_CORE="${SOLR_CORE:-cards}"
SOLR_URI="${SOLR_URI:-http://localhost:${SOLR_PORT}/solr}"

if [[ ! -x "${TREC_EVAL_BIN}" ]]; then
    printf 'trec_eval was not found at %s. Clone and build it as described in evaluation/README.md.\n' \
        "${TREC_EVAL_BIN}" >&2
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

uv run python "${EVALUATION_DIR}/scripts/qrels2trec.py" \
    --qrels "${QRELS_DIR}" > "${OUTPUT_DIR}/qrels.trec"

uv run python "${EVALUATION_DIR}/scripts/query_solr.py" \
    --queries "${QUERIES_DIR}" \
    --uri "${SOLR_URI}" \
    --collection "${SOLR_CORE}" \
| uv run python "${EVALUATION_DIR}/scripts/solr2trec.py" \
    > "${OUTPUT_DIR}/results.trec"

"${TREC_EVAL_BIN}" \
    -q \
    -m all_trec \
    "${OUTPUT_DIR}/qrels.trec" \
    "${OUTPUT_DIR}/results.trec" \
    | tee "${OUTPUT_DIR}/metrics.txt"
