#!/usr/bin/env bash
# vim: ai:sw=4:ts=4:sta:et:fo=croql:nu
#
# Copyright 2022 Google.
# This software is provided as-is, without warranty or representation for any use or purpose.
# Your use of it is subject to your agreement with Google.

DEFAULT_ENV_CR_CONCURRENCY=80
ENV_CR_CONCURRENCY=${ENV_CR_CONCURRENCY:-$DEFAULT_ENV_CR_CONCURRENCY}
DEFAULT_PORT=8080
PORT=${PORT:-$DEFAULT_PORT}
APPLICATION=${1:-$FLASK_APP}

# Source https://docs.gunicorn.org/en/stable/design.html#how-many-workers
CORES=$(nproc --all)
(( WORKERS=2 * ${CORES} + 1 ))
(( THREADS=(${ENV_CR_CONCURRENCY} + ${WORKERS} - 1) / ${WORKERS} ))
echo "CPU cores '${CORES}'. Concurrency '${ENV_CR_CONCURRENCY}', workers '${WORKERS}', and threads '${THREADS}'"

echo "Starting Gunicorn application '${APPLICATION}' at port '${PORT}'"
gunicorn \
  --bind ":${PORT}" \
  --workers ${WORKERS} \
  --threads ${THREADS} \
  --timeout 0 \
  ${APPLICATION}
