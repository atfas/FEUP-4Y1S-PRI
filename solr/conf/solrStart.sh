#!/usr/bin/env bash

set -Eeuo pipefail

CONTAINER_NAME="cards_solr"
CORE_NAME="cards"
SOLR_IMAGE="solr:10"
SOLR_PORT="${SOLR_PORT:-8983}"
SOLR_URL="http://localhost:${SOLR_PORT}"

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
SOLR_DATA_DIR="${PROJECT_ROOT}/data/_solr"
DATA_FILE="${SOLR_DATA_DIR}/databank.json"
SCHEMA_FILE="${SOLR_DATA_DIR}/databank_schema.json"

if [[ ! -f "${DATA_FILE}" || ! -f "${SCHEMA_FILE}" ]]; then
    printf 'Missing generated Solr files in %s. Run "make flatten" first.\n' \
        "${SOLR_DATA_DIR}" >&2
    exit 1
fi

if docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1 &&
    [[ "$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}")" == "created" ]]; then
    docker rm "${CONTAINER_NAME}" >/dev/null
fi

port_owner="$(
    docker ps --filter "publish=${SOLR_PORT}" --format '{{.Names}}' |
        grep -v "^${CONTAINER_NAME}$" |
        head -n 1 || true
)"
if [[ -n "${port_owner}" ]]; then
    printf 'Port %s is already used by container "%s". Stop it or run with another port, for example SOLR_PORT=8984 %s.\n' \
        "${SOLR_PORT}" "${port_owner}" "$0" >&2
    exit 1
fi

if ! docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    docker run \
        --name "${CONTAINER_NAME}" \
        --publish "${SOLR_PORT}:8983" \
        --volume "${SOLR_DATA_DIR}:/data/_solr:ro" \
        --detach \
        "${SOLR_IMAGE}" \
        solr-precreate "${CORE_NAME}"
elif [[ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}")" != "true" ]]; then
    docker start "${CONTAINER_NAME}" >/dev/null
fi

printf 'Waiting for Solr core "%s"...\n' "${CORE_NAME}"
until curl --fail --silent --show-error \
    "${SOLR_URL}/solr/${CORE_NAME}/admin/ping" >/dev/null; do
    sleep 2
done

# Recreate the core so rerunning this script produces the same index and schema.
docker exec "${CONTAINER_NAME}" solr delete -c "${CORE_NAME}" >/dev/null
docker exec "${CONTAINER_NAME}" solr create -c "${CORE_NAME}" >/dev/null

until curl --fail --silent --show-error \
    "${SOLR_URL}/solr/${CORE_NAME}/admin/ping" >/dev/null; do
    sleep 2
done

printf 'Applying schema...\n'
curl --fail --silent --show-error \
    --request POST \
    --header 'Content-Type: application/json' \
    --data-binary "@${SCHEMA_FILE}" \
    "${SOLR_URL}/solr/${CORE_NAME}/schema"

printf 'Indexing data...\n'
docker exec "${CONTAINER_NAME}" solr post \
    -c "${CORE_NAME}" \
    "/data/_solr/$(basename -- "${DATA_FILE}")"

printf 'Solr is ready at %s/solr/%s\n' "${SOLR_URL}" "${CORE_NAME}"