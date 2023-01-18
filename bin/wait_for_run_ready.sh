#!/usr/bin/env bash

VALID_LATEST_STATUS="True"
VALID_LATEST_TYPE="Ready"
SEPARATOR="@"
VALID_TYPE_STATUS="${VALID_LATEST_TYPE}${SEPARATOR}${VALID_LATEST_STATUS}"

REGION=${REGION:-"europe-west3"}

MAX_RETRIES=${MAX_RETRIES:-5}
RETRY_SLEEP_IN_SECS=${RETRY_SLEEP_IN_SECS:-10}

PATH_LATEST_STATUS="status.conditions[0].status"
PATH_LATEST_TYPE="status.conditions[0].type"

SERVICE_LOG_STR="${SERVICE_NAME}@${REGION} in ${PROJECT}"

function latest_status_condition
{
  local STATUS_PATH=${1}

  gcloud run services describe "${SERVICE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT}" \
    --format="value(${STATUS_PATH})"
}

function latest_type_status
{
  local LATEST_STATUS=""
  local LATEST_TYPE=""

  LATEST_STATUS=$(latest_status_condition "${PATH_LATEST_STATUS}")
  LATEST_TYPE=$(latest_status_condition "${PATH_LATEST_TYPE}")

  echo "${LATEST_TYPE}${SEPARATOR}${LATEST_STATUS}"
}

function is_ready
{
  local LATEST_TYPE_STATUS=""
  local RESULT=1

  LATEST_TYPE_STATUS=$(latest_type_status)

  if [ "${LATEST_TYPE_STATUS}" == "${VALID_TYPE_STATUS}" ]
  then
    RESULT=0
  fi
  return ${RESULT}
}

function wait_for_ready
{
  local IS_READY=1
  local RESULT=1

  local LATEST_TYPE_STATUS=""

  for SEC in $(seq 1 "${MAX_RETRIES}")
  do
    is_ready
    IS_READY=${?}
    if [ ${IS_READY} -eq 0 ]
    then
      RESULT=0
      break
    fi
    LATEST_TYPE_STATUS=$(latest_type_status)
    echo "Service ${SERVICE_LOG_STR} is **NOT** ready. Got: <${LATEST_TYPE_STATUS}>. Expected: <${VALID_TYPE_STATUS}>"
    echo "Retry ${SEC} of ${MAX_RETRIES}, waiting ${RETRY_SLEEP_IN_SECS} seconds."
    sleep "${RETRY_SLEEP_IN_SECS}"
  done

  LATEST_TYPE_STATUS=$(latest_type_status)
  if [ ${RESULT} -eq 0 ]
  then
    echo "[OK] Service ${SERVICE_LOG_STR} is ready. Got: <${LATEST_TYPE_STATUS}>. Expected: <${VALID_TYPE_STATUS}>"
  else
    echo "[ERROR] Service ${SERVICE_LOG_STR} is not ready. Got: <${LATEST_TYPE_STATUS}>. Expected: <${VALID_TYPE_STATUS}>"
  fi

  return ${RESULT}
}

echo "Waiting for service ${SERVICE_LOG_STR} to be ready <${VALID_TYPE_STATUS}>"
echo "Max retries is ${MAX_RETRIES} with sleep time of ${RETRY_SLEEP_IN_SECS} seconds in between."

wait_for_ready
exit ${?}
