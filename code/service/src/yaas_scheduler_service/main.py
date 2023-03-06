# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCP Cloud Run entry point:

* https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364
"""
from typing import Any, Dict

import flask
from yaas_command import pubsub_dispatcher
from yaas_common import logger

from yaas_flask import cloud_run, flask_gunicorn
from yaas_scheduler_service import entry

_LOGGER = logger.get(__name__)

BLUEPRINT = flask.Blueprint("main", __name__, url_prefix="/")


@BLUEPRINT.route("/config", methods=["GET"])
def configuration() -> str:
    """Just return the current :py:class:`config.Config` as JSON.

    `curl`::
        curl http://localhost:8080/config
    """
    return cloud_run.configuration()


@BLUEPRINT.route("/command", methods=["POST"])
async def command() -> str:
    # pylint: disable=anomalous-backslash-in-string,line-too-long
    """Wrapper to :py:func:`entry.command`.

    `curl`::
        PERIOD_DAYS="3"
        PERIOD_MINUTES=$(expr ${PERIOD_DAYS} \* 24 \* 60)
        DATA="{\"type\": \"UPDATE_CALENDAR_CACHE\", \"range\": {\"period_minutes\":${PERIOD_MINUTES}, \"now_diff_minutes\":10}}"
        DATA_BASE64=$(echo ${DATA} | base64)
        curl \
            -d "{\"data\":\"${DATA_BASE64}\"}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/command
    """

    # pylint: enable=anomalous-backslash-in-string,line-too-long
    async def async_kwargs_fn(event: flask.Request) -> Dict[str, Any]:
        return dict(
            value=pubsub_dispatcher.command_from_event(event=event),
            configuration=cloud_run.read_configuration(),
        )

    async_fn = entry.process_command
    return await cloud_run.handle_request(what="command", async_kwargs_fn=async_kwargs_fn, async_fn=async_fn)


@BLUEPRINT.route("/update-calendar-credentials-secret", methods=["POST"])
async def update_calendar_credentials() -> str:
    """Wrapper to :py:func:`entry.update_calendar_credentials`.

    `curl`::
        curl \
            -d "{}" \
            -H "Content-Type: application/json" \
            -X POST \
            http://localhost:8080/update-calendar-credentials-secret
    """

    async def async_kwargs_fn(_: flask.Request) -> Dict[str, Any]:
        return dict(configuration=cloud_run.read_configuration())

    async_fn = (entry.update_calendar_credentials,)
    return await cloud_run.handle_request(
        what="update_calendar_credentials", async_kwargs_fn=async_kwargs_fn, async_fn=async_fn
    )


@BLUEPRINT.route("/update-cache", methods=["POST"])
async def update_cache() -> str:
    # pylint: disable=anomalous-backslash-in-string
    """Wrapper to :py:func:`entry.update_cache`.

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
    async def async_kwargs_fn(event: flask.Request) -> Dict[str, Any]:
        update_range = pubsub_dispatcher.range_from_event(event=event)
        start_ts_utc, end_ts_utc = update_range.timestamp_range()
        return dict(
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            configuration=cloud_run.read_configuration(),
        )

    async_fn = entry.update_cache
    return await cloud_run.handle_request(what="update_cache", async_kwargs_fn=async_kwargs_fn, async_fn=async_fn)


@BLUEPRINT.route("/send-requests", methods=["POST"])
async def send_requests() -> str:
    """Wrapper to :py:func:`entry.send_requests`.

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

    async def async_kwargs_fn(event: flask.Request) -> Dict[str, Any]:
        send_range = pubsub_dispatcher.range_from_event(event=event)
        start_ts_utc, end_ts_utc = send_range.timestamp_range()
        return dict(
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            configuration=cloud_run.read_configuration(),
            raise_if_invalid_request=False,
        )

    async_fn = entry.send_requests
    return await cloud_run.handle_request(what="send_requests", async_kwargs_fn=async_kwargs_fn, async_fn=async_fn)


# YES, it needs to be defined here, after all @BLUEPRINT
APPLICATION = cloud_run.create_app(BLUEPRINT)


def main():
    """To test::

    export CONFIG_BUCKET_NAME=yaas_cache
    export CONFIG_OBJECT_PATH=yaas/config.json
    poetry run scheduler
    """
    flask_gunicorn.run(APPLICATION)


if __name__ == "__main__":
    main()
