# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP Cloud Run entry point:
* https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364
"""
# pylint: enable=line-too-long
import os

import flask

from yaas import logger
from yaas.dto import config
from yaas.entry_point import entry, pubsub_dispatcher
from yaas.gcp import gcs
from yaas.scaler import gcs_batch, standard

_LOGGER = logger.get(__name__)
MAIN_BP = flask.Blueprint("main", __name__, url_prefix="/")

CONFIG_BUCKET_NAME_ENV_VAR: str = "CONFIG_BUCKET_NAME"
CONFIG_OBJECT_PATH_ENV_VAR: str = "CONFIG_OBJECT_PATH"


#########
# Flask #
#########


def create_app(  # pylint: disable=unused-argument,keyword-arg-before-vararg
    test_config=None, *args, **kwargs
) -> flask.Flask:
    """
    As in https://flask.palletsprojects.com/en/2.2.x/tutorial/factory/

    Args:
        test_config:
        *args:
        **kwargs:

    Returns:

    """
    app = flask.Flask(__name__, instance_relative_config=False)
    if test_config:
        app.config.from_mapping(test_config)
    app.register_blueprint(MAIN_BP)
    return app


def _configuration() -> config.Config:
    bucket_name = os.getenv(CONFIG_BUCKET_NAME_ENV_VAR)
    object_path = os.getenv(CONFIG_OBJECT_PATH_ENV_VAR)
    config_json = gcs.read_object(
        bucket_name=bucket_name, object_path=object_path, warn_read_failure=True
    )
    return config.Config.from_json(config_json)


#############
# Cloud Run #
#############


@MAIN_BP.route("/config", methods=["GET"])
def configuration() -> str:
    """
    Just return the current :py:class:`config.Config` as JSON.

    `curl`::
        curl http://localhost:8080/config

    """
    _LOGGER.debug(
        "Request data: <%s>(%s)", flask.request.data, type(flask.request.data)
    )
    _LOGGER.info("Calling %s", configuration.__name__)
    return flask.jsonify(_configuration().as_dict())


@MAIN_BP.route("/update-calendar-credentials-secret", methods=["POST"])
async def update_calendar_credentials() -> str:
    # pylint: disable=anomalous-backslash-in-string
    """
    Wrapper to :py:func:`entry.update_calendar_credentials`.

    `curl`::
        curl \
            -d "{}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/update-calendar-credentials-secret
    """
    # pylint: enable=anomalous-backslash-in-string
    _LOGGER.debug(
        "Request data: <%s>(%s)", flask.request.data, type(flask.request.data)
    )
    try:
        _LOGGER.info("Calling %s", update_calendar_credentials.__name__)
        await entry.update_calendar_credentials(
            configuration=_configuration(),
        )
        result = flask.make_response(("OK", 200))
    except Exception as err:  # pylint: disable=broad-except
        msg = f"Could not update calendar credentials. Error: {err}"
        _LOGGER.exception(msg)
        result = flask.jsonify({"error": msg})
    return result


@MAIN_BP.route("/update-cache", methods=["POST"])
async def update_cache() -> str:
    # pylint: disable=anomalous-backslash-in-string
    """
    Wrapper to :py:func:`entry.update_cache`.

    `curl`::
        PERIOD_DAYS="3"
        PERIOD_MINUTES=$(expr ${PERIOD_DAYS} \* 24 \* 60)
        DATA="{\"period_minutes\":${PERIOD_MINUTES}, \"now_diff_minutes\":10}"
        DATA_BASE64=$(echo ${DATA} | base64)
        curl \
            -d "{\"data\":\"${DATA_BASE64}\"}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/update-cache
    """
    # pylint: enable=anomalous-backslash-in-string
    _LOGGER.debug(
        "Request data: <%s>(%s)", flask.request.data, type(flask.request.data)
    )
    try:
        update_range = pubsub_dispatcher.range_from_event(event=flask.request)
        _LOGGER.info(
            "Calling %s with range %s", update_cache.__name__, update_range.as_log_str()
        )
        start_ts_utc, end_ts_utc = update_range.timestamp_range()
        await entry.update_cache(
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            configuration=_configuration(),
        )
        result = flask.make_response(("OK", 200))
    except Exception as err:  # pylint: disable=broad-except
        msg = f"Could not update cache. Error: {err}"
        _LOGGER.exception(msg)
        result = flask.jsonify({"error": msg})
    return result


@MAIN_BP.route("/send-requests", methods=["POST"])
async def send_requests() -> str:
    # pylint: disable=anomalous-backslash-in-string
    """
    Wrapper to :py:func:`entry.send_requests`.

    `curl`::
        PERIOD_MINUTES=10
        DATA="{\"period_minutes\":${PERIOD_MINUTES}, \"now_diff_minutes\":-1}"
        DATA_BASE64=$(echo ${DATA} | base64)
        curl \
            -d "{\"data\":\"${DATA_BASE64}\"}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/send-requests
    """
    # pylint: enable=anomalous-backslash-in-string
    _LOGGER.debug(
        "Request data: <%s>(%s)", flask.request.data, type(flask.request.data)
    )
    try:
        send_range = pubsub_dispatcher.range_from_event(event=flask.request)
        _LOGGER.info(
            "Calling %s with range %s", send_requests.__name__, send_range.as_log_str()
        )
        start_ts_utc, end_ts_utc = send_range.timestamp_range()
        await entry.send_requests(
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            configuration=_configuration(),
            raise_if_invalid_request=False,
        )
        result = flask.make_response(("OK", 200))
    except Exception as err:  # pylint: disable=broad-except
        msg = f"Could not send requests. Error: {err}"
        _LOGGER.exception(msg)
        result = flask.jsonify({"error": msg})
    return result


@MAIN_BP.route("/enact-standard-requests", methods=["POST"])
async def enact_standard_requests() -> str:
    # pylint: disable=anomalous-backslash-in-string,line-too-long
    """
    Wrapper to :py:func:`entry.enact_requests`.

    `curl`::
        REGION="europe-west3"
        PROJECT=$(gcloud config get project)
        RESOURCE="projects/${PROJECT}/locations/${REGION}/services/hello"
        COMMAND="min_instances 11"
        TIMESTAMP=$(date -u +%s)
        DATA="{\"collection\": [{\"topic\": \"standard\", \"resource\": \"${RESOURCE}\", \"command\": \"${COMMAND}\", \"timestamp_utc\": ${TIMESTAMP}, \"original_json_event\": null}]}"
        DATA_BASE64=$(echo ${DATA} | base64)
        curl \
            -d "{\"data\":\"${DATA_BASE64}\"}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/enact-standard-requests
    """
    # pylint: enable=anomalous-backslash-in-string,line-too-long
    _LOGGER.debug(
        "Request data: <%s>(%s)", flask.request.data, type(flask.request.data)
    )
    try:
        _LOGGER.info("Calling %s", enact_standard_requests.__name__)
        parser = standard.StandardScalingCommandParser(strict_mode=False)
        await entry.enact_requests(parser=parser, pubsub_event=flask.request)
        result = flask.make_response(("OK", 200))
    except Exception as err:  # pylint: disable=broad-except
        msg = f"Could not enact request. Error: {err}"
        _LOGGER.exception(msg)
        result = flask.jsonify({"error": msg})
    return result


@MAIN_BP.route("/enact-gcs-requests", methods=["POST"])
async def enact_gcs_requests() -> str:
    # pylint: disable=anomalous-backslash-in-string,line-too-long
    """
    Wrapper to :py:func:`entry.enact_requests`.

    Create GCS profile::
        BUCKET_NAME="<MY_BUCKET_NAME>"
        PROFILE_PREFIX="yaas/scaling_profiles"
        PROFILE_NAME="hello_min_instances_11"

        REGION="europe-west3"
        PROJECT=$(gcloud config get project)

        TMP=$(mktemp)
        cat > ${TMP} << __END__
        standard | projects/${PROJECT}/locations/${REGION}/services/hello | min_instances 11
        __END__

        gsutil cp ${TMP} gs://${BUCKET_NAME}/${PROFILE_PREFIX}/${PROFILE_NAME}


    `curl`::
        REGION="europe-west3"
        PROJECT=$(gcloud config get project)
        COMMAND="${PROFILE_PREFIX}/${PROFILE_NAME}"
        TIMESTAMP=$(date -u +%s)
        DATA="{\"collection\": [{\"topic\": \"gcs\", \"resource\": \"${BUCKET_NAME}\", \"command\": \"${COMMAND}\", \"timestamp_utc\": ${TIMESTAMP}, \"original_json_event\": null}]}"
        DATA_BASE64=$(echo ${DATA} | base64)
        curl \
            -d "{\"data\":\"${DATA_BASE64}\"}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/enact-gcs-requests
    """
    # pylint: enable=anomalous-backslash-in-string,line-too-long
    _LOGGER.debug(
        "Request data: <%s>(%s)", flask.request.data, type(flask.request.data)
    )
    try:
        _LOGGER.info("Calling %s", enact_standard_requests.__name__)
        parser = gcs_batch.GcsBatchCommandParser(
            topic_to_pubsub=_configuration().topic_to_pubsub
        )
        await entry.enact_requests(parser=parser, pubsub_event=flask.request)
        result = flask.make_response(("OK", 200))
    except Exception as err:  # pylint: disable=broad-except
        msg = f"Could not enact request. Error: {err}"
        _LOGGER.exception(msg)
        result = flask.jsonify({"error": msg})
    return result


def _main():
    """
    To test::
        export CONFIG_BUCKET_NAME=yaas_cache
        export CONFIG_OBJECT_PATH=yaas.cfg
        python -m yaas.entry_point.cloud_run
    """
    port = int(os.getenv("PORT")) if os.getenv("PORT") else 8080
    create_app().run(host="127.0.0.1", port=port, debug=True)


if __name__ == "__main__":
    _main()
