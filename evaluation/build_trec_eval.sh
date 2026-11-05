#!/usr/bin/env bash

set -Eeuo pipefail

EVALUATION_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TREC_EVAL_DIR="${EVALUATION_DIR}/trec_eval"
TREC_EVAL_BIN="${TREC_EVAL_DIR}/trec_eval"

if [[ ! -d "${TREC_EVAL_DIR}" ]]; then
    git clone https://github.com/usnistgov/trec_eval.git "${TREC_EVAL_DIR}"
fi

make -C "${TREC_EVAL_DIR}"

if [[ ! -x "${TREC_EVAL_BIN}" ]]; then
    printf 'Failed to build %s\n' "${TREC_EVAL_BIN}" >&2
    exit 1
fi
