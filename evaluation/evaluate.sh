#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
EVALUATION_DIR="${PROJECT_ROOT}/evaluation"
QUERIES_DIR="${EVALUATION_DIR}/queries"
QRELS_DIR="${EVALUATION_DIR}/qrels"
TREC_EVAL_BIN="${TREC_EVAL_BIN:-${EVALUATION_DIR}/trec_eval/trec_eval}"
SOLR_PORT="${SOLR_PORT:-8983}"
SOLR_CORE="${SOLR_CORE:-cards}"
SOLR_URI="${SOLR_URI:-http://localhost:${SOLR_PORT}/solr}"

case "${SYSTEM:-}" in
    default|advanced) ;;
    *)
        printf 'Set SYSTEM to default or advanced.\n' >&2
        exit 1
        ;;
esac

OUTPUT_DIR="${EVALUATION_DIR}/output/${SYSTEM}"
SYSTEM_CONFIG="${PROJECT_ROOT}/solr/conf/${SYSTEM}-system.json"

if [[ ! -x "${TREC_EVAL_BIN}" ]]; then
    printf 'trec_eval was not found at %s. Clone and build it as described in evaluation/README.md.\n' \
        "${TREC_EVAL_BIN}" >&2
    exit 1
fi

printf 'Selecting %s search system on %s/%s...\n' "${SYSTEM}" "${SOLR_URI%/}" "${SOLR_CORE}" >&2
curl --fail --silent --show-error \
    --request POST \
    --header 'Content-Type: application/json' \
    --data-binary "@${SYSTEM_CONFIG}" \
    "${SOLR_URI%/}/${SOLR_CORE}/config" >/dev/null

curl --fail --silent --show-error \
    "${SOLR_URI%/}/${SOLR_CORE}/config/requestHandler" |
    python3 -c '
import json
import sys
from pathlib import Path

expected = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["update-requesthandler"]
actual = json.load(sys.stdin)["config"]["requestHandler"]["/select"]
if actual.get("class") != expected["class"] or actual.get("defaults") != expected["defaults"]:
    raise SystemExit(f"Failed to activate SYSTEM={sys.argv[2]}: Solr /select configuration does not match.")
' "${SYSTEM_CONFIG}" "${SYSTEM}"

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
