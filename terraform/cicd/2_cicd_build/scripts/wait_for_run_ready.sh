#!/usr/bin/env bash
# vim: ai:sw=4:ts=4:sta:et:fo=croql:nu
#
# Copyright 2022 Google.
# This software is provided as-is, without warranty or representation for any use or purpose.
# Your use of it is subject to your agreement with Google.

# Needs to be the first thing
ALL_CLI_ARGS="${*}"

###############################################################
### DEPENDENCIES DEFINITIONS
###############################################################

LINUX_GETOPT_CMD="getopt"
MAC_GETOPT_CMD="/usr/local/opt/gnu-getopt/bin/getopt"
GETOPT_CMD="${LINUX_GETOPT_CMD}"

unset REQUIRED_UTILITIES
set -a REQUIRED_UTILITIES
REQUIRED_UTILITIES=(
  "bash"
  "getopt"
  "gcloud"
)
if [ "Darwin" == $(uname -s) ]; then
  REQUIRED_UTILITIES+=("${MAC_GETOPT_CMD}")
  GETOPT_CMD="${MAC_GETOPT_CMD}"
fi

###############################################################
### CLI DEFINITIONS
###############################################################

# CLI
# Source: https://gist.github.com/magnetikonline/22c1eb412daa350eeceee76c97519da8
OPT_HELP="help"
OPT_REGION="region"
OPT_PRJ_ID="project"
OPT_NAME="service"
OPT_MAX_RETRIES="retries"
OPT_RETRY_RETRY_SLEEP_IN_SECS="retry-wait"

unset ARGUMENT_FLAG_LIST
set -a ARGUMENT_FLAG_LIST
ARGUMENT_FLAG_LIST=(
  "${OPT_HELP}"
)

unset ARGUMENT_LIST
set -a ARGUMENT_LIST
ARGUMENT_LIST=(
  "${OPT_REGION}"
  "${OPT_PRJ_ID}"
  "${OPT_NAME}"
  "${OPT_MAX_RETRIES}"
  "${OPT_RETRY_RETRY_SLEEP_IN_SECS}"
)

# read arguments
CLI_ARGS=$(
  ${GETOPT_CMD} \
    --options "h" \
    --longoptions "$(printf "%s," "${ARGUMENT_FLAG_LIST[@]}")$(printf "%s:," "${ARGUMENT_LIST[@]:1}")${ARGUMENT_LIST[0]}:" \
    --name "$(basename "${0}")" \
    -- ${ALL_CLI_ARGS}
)

###############################################################
### DEFAULT DEFINITIONS
###############################################################

DEFAULT_REGION="europe-west3"
DEFAULT_MAX_RETRIES="5"
DEFAULT_RETRY_RETRY_SLEEP_IN_SECS="10"

###############################################################
### GLOBAL DEFINITIONS
###############################################################

# Cloud Run status x-path for validation
PATH_LATEST_STATUS="status.conditions[0].status"
PATH_LATEST_TYPE="status.conditions[0].type"

# Cloud Run expected values
VALID_LATEST_STATUS="True"
VALID_LATEST_TYPE="Ready"
# Derived expected values' string
SEPARATOR="@"
VALID_TYPE_STATUS="${VALID_LATEST_TYPE}${SEPARATOR}${VALID_LATEST_STATUS}"

# To be set by CLI options
PROJECT=""
SERVICE_NAME=""
REGION="${DEFAULT_REGION}"
MAX_RETRIES="${DEFAULT_MAX_RETRIES}"
RETRY_SLEEP_IN_SECS="${DEFAULT_RETRY_RETRY_SLEEP_IN_SECS}"
# Derived variables from CLI options
SERVICE_LOG_STR=""

# Required options
REQUIRED_OPTS_SEP="@@"
unset REQUIRED_OPTS
set -a REQUIRED_OPTS
# GLOBAL_VAR@@CLI_OPT
REQUIRED_OPTS=(
    "PROJECT${REQUIRED_OPTS_SEP}${OPT_PRJ_ID}"
    "SERVICE_NAME${REQUIRED_OPTS_SEP}${OPT_NAME}"
)

###############################################################
### DEPENDENCIES
###############################################################

function check_utilities {
  # 0 == true
  local HAS_ALL=0
  # shellcheck disable=SC2068
  for U in ${REQUIRED_UTILITIES[@]}; do
    if [ -z "$(which ${U})" ]; then
      echo "Missing utility ${U}"
      HAS_ALL=1
    fi
  done
  if [ ${HAS_ALL} -ne 0 ]; then
    echo "Missing required utilities. Check logs."
    exit 1
  fi
}

function check_opts
{
    for VAR_OPT in ${REQUIRED_OPTS[@]}
    do
        local VAR_OPT_SPACE="${VAR_OPT//$REQUIRED_OPTS_SEP/ }"
        local VAR="${VAR_OPT_SPACE%% *}"
        local OPT="${VAR_OPT_SPACE##* }"
        local VAL="${!VAR}"
        if [ -z "${VAL}" ]; then
            echo "Missing mandatory argument [--${OPT}]"
            help
            exit 1
        fi
    done
}

###############################################################
### HELP
###############################################################

function help {
  echo
  echo -e "Usage:"
  echo -e "\t${0} [-h | --${OPT_HELP}]"
  echo -e "\t\t--${OPT_PRJ_ID} <PROJECT_ID>"
  echo -e "\t\t--${OPT_NAME} <SERVICE_NAME>"
  echo -e "\t\t[--${OPT_REGION} <REGION>]"
  echo -e "\t\t[--${OPT_MAX_RETRIES} <MAX_RETRIES>]"
  echo -e "\t\t[--${OPT_RETRY_RETRY_SLEEP_IN_SECS} <RETRY_SLEEP_IN_SECS>]"
  echo -e "Where:"
  echo -e "\t-h | --${OPT_HELP} this help"
  echo -e "\t--${OPT_PRJ_ID} with <PROJECT_ID> being the project where the Cloud Run service resides"
  echo -e "\t--${OPT_NAME} with <SERVICE_NAME> being the Cloud Run service name"
  echo -e "\t--${OPT_REGION} with <REGION> overwriting the default region, which is '${DEFAULT_REGION}'"
  echo -e "\t--${OPT_MAX_RETRIES} with <MAX_RETRIES> being the maximum amount of times to try to wait for the service to be ready, default is '${DEFAULT_MAX_RETRIES}'"
  echo -e "\t--${OPT_RETRY_RETRY_SLEEP_IN_SECS} with <RETRY_SLEEP_IN_SECS> specifying the amount of time (in seconds) to wait between retries, default is '${DEFAULT_RETRY_RETRY_SLEEP_IN_SECS}'"
  echo
  echo -e "Example:"
  echo -e "\t${0} \\"
  echo -e "\t\t--${OPT_PRJ_ID} MY_PROJECT_ID \\"
  echo -e "\t\t--${OPT_NAME} MY_CLOUD_RUN_SERVICE_NAME \\"
  echo -e "\t\t--${OPT_REGION} ${DEFAULT_REGION} \\"
  echo -e "\t\t--${OPT_MAX_RETRIES} ${DEFAULT_MAX_RETRIES} \\"
  echo -e "\t\t--${OPT_RETRY_RETRY_SLEEP_IN_SECS} ${DEFAULT_RETRY_RETRY_SLEEP_IN_SECS}"
  echo
}

###############################################################
### Helper functions
###############################################################

function set_globals
{
  REGION="${REGION:-$DEFAULT_REGION}"
  MAX_RETRIES="${MAX_RETRIES:-$DEFAULT_MAX_RETRIES}"
  RETRY_SLEEP_IN_SECS="${RETRY_SLEEP_IN_SECS:-$DEFAULT_RETRY_RETRY_SLEEP_IN_SECS}"
  # Derived
  SERVICE_LOG_STR="${SERVICE_NAME}@${REGION} in ${PROJECT}"
}

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

###############################################################
### Exists?
###############################################################

function is_service_created
{
  local RESULT=1

  local FOUND=$(gcloud run services list \
    --region="${REGION}" \
    --project="${PROJECT}" \
    --format=json \
    | jq -c -r ".[].metadata.name" \
    | grep -e "^${SERVICE_NAME}$"
  )
  if [ "${FOUND}" == "${SERVICE_NAME}" ]
  then
    RESULT=0
  fi
  return ${RESULT}
}

###############################################################
### Wait function
###############################################################

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

###############################################################
### MAIN
###############################################################

function main {
  set_globals
  echo "Waiting for service ${SERVICE_LOG_STR} to be ready <${VALID_TYPE_STATUS}>"
  echo "Max retries is ${MAX_RETRIES} with sleep time of ${RETRY_SLEEP_IN_SECS} seconds in between."
  is_service_created
  local EXISTS=${?}
  if [ ${EXISTS} -eq 0 ]
  then
    wait_for_ready
    exit ${?}
  else
    echo "Service ${SERVICE_LOG_STR} does not exist yet."
  fi
}

###############################################################
### PARSING CLI
###############################################################

# Source: https://gist.github.com/magnetikonline/22c1eb412daa350eeceee76c97519da8

eval set -- "${CLI_ARGS}"
# shellcheck disable=SC2145
echo "CLI args = [${@}]"

while [[ ${#} -gt 0 ]]; do
  case ${1} in
  ## Options without arguments
  -h | --${OPT_HELP})
    help
    exit 0
    ;;
    ## Options with arguments
  --${OPT_PRJ_ID})
    PROJECT=${2}
    shift 2
    ;;
  --${OPT_NAME})
    SERVICE_NAME=${2}
    shift 2
    ;;
  --${OPT_REGION})
    REGION=${2}
    shift 2
    ;;
  --${OPT_MAX_RETRIES})
    MAX_RETRIES=${2}
    shift 2
    ;;
  --${OPT_RETRY_RETRY_SLEEP_IN_SECS})
    RETRY_SLEEP_IN_SECS=${2}
    shift 2
    ;;
  *)
    break
    ;;
  esac
done

check_utilities
check_opts
main