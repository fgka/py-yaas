# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCP Cloud Run entry point:

* https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364
"""
import os
from typing import Any, Dict

import flask
from yaas_common import logger
from yaas_scaler import gcs_batch, standard

from yaas_flask import cloud_run, flask_gunicorn
from yaas_scaler_service import entry

_LOGGER = logger.get(__name__)

BLUEPRINT = flask.Blueprint("main", __name__, url_prefix="/")


@BLUEPRINT.route("/config", methods=["GET"])
def configuration() -> str:
    """Just return the current :py:class:`config.Config` as JSON.

    `curl`::
        curl http://localhost:8080/config
    """
    return cloud_run.configuration()


@BLUEPRINT.route("/enact-standard-requests", methods=["POST"])
async def enact_standard_requests() -> str:
    # pylint: disable=line-too-long
    """Wrapper to :py:func:`entry.enact_requests`.

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

    # pylint: enable=line-too-long
    async def async_kwargs_fn(event: flask.Request) -> Dict[str, Any]:
        return dict(
            parser=standard.StandardScalingCommandParser(strict_mode=False),
            pubsub_event=event,
        )

    async_fn = entry.enact_requests
    return await cloud_run.handle_request(what="enact-standard", async_kwargs_fn=async_kwargs_fn, async_fn=async_fn)


@BLUEPRINT.route("/enact-gcs-requests", methods=["POST"])
async def enact_gcs_requests() -> str:
    # pylint: disable=line-too-long
    """Wrapper to :py:func:`entry.enact_requests`.

    Create GCS profile::
        BUCKET_NAME="<MY_BUCKET_NAME>"
        PROFILE_PREFIX="yaas_gcp-scaler-scheduler_service-common/scaling_profiles"
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

    # pylint: enable=line-too-long
    async def async_kwargs_fn(_: flask.Request) -> Dict[str, Any]:
        return dict(
            parser=gcs_batch.GcsBatchCommandParser(topic_to_pubsub=cloud_run.read_configuration().topic_to_pubsub)
        )

    async_fn = entry.enact_requests
    return await cloud_run.handle_request(what="enact-gcs", async_kwargs_fn=async_kwargs_fn, async_fn=async_fn)


# YES, it needs to be defined here, after all @BLUEPRINT
APPLICATION = cloud_run.create_app(BLUEPRINT)


def main():
    """To test::

    export CONFIG_BUCKET_NAME=yaas_cache
    export CONFIG_OBJECT_PATH=yaas/config.json
    poetry run scaler
    """
    flask_gunicorn.run(APPLICATION)


if __name__ == "__main__":
    main()
