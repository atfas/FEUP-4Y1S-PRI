#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOLR_PORT="${SOLR_PORT:-8983}"
SOLR_URL="http://localhost:${SOLR_PORT}"
CORE_NAME="cards"
CONFIG_FILE="${SCRIPT_DIR}/default-system.json"

curl --fail --silent --show-error \
    "${SOLR_URL}/solr/${CORE_NAME}/admin/ping" >/dev/null

printf 'Setting Solr search system to default...\n'
curl --fail --silent --show-error \
    --request POST \
    --header 'Content-Type: application/json' \
    --data-binary "@${CONFIG_FILE}" \
    "${SOLR_URL}/solr/${CORE_NAME}/config"

printf 'Default search system is active at %s/solr/%s/select\n' \
    "${SOLR_URL}" "${CORE_NAME}"
