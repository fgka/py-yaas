# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCP Cloud Run entry point:

* https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364
"""
import os
from typing import Any, Callable, Dict, Optional, Tuple

import flask
from yaas_common import logger
from yaas_config import config, resolve_config
from yaas_gcp import gcs

_LOGGER = logger.get(__name__)

CONFIG_BUCKET_NAME_ENV_VAR: str = "CONFIG_BUCKET_NAME"
"""
Bucket name is expected to be the content of this environment variable.
"""
CONFIG_OBJECT_PATH_ENV_VAR: str = "CONFIG_OBJECT_PATH"
"""
The path to the configuration object,
inside the bucket defined by :py:data:`CONFIG_BUCKET_NAME_ENV_VAR`.
"""


#########
# Flask #
#########


def create_app(  # pylint: disable=unused-argument,keyword-arg-before-vararg
    blueprint: flask.Blueprint, test_config: Optional[Dict[str, Any]] = None, *args, **kwargs
) -> flask.Flask:
    """As in https://flask.palletsprojects.com/en/2.2.x/tutorial/factory/

    Args:
        blueprint: what to register
        test_config: if to overwrite config in app
        *args: to ignore
        **kwargs: to ignore

    Returns:
    """
    app = flask.Flask(__name__, instance_relative_config=False)
    if test_config:
        app.config.from_mapping(test_config)
    app.register_blueprint(blueprint)
    return app


def read_configuration() -> config.Config:
    """Based on the environment variables below, reads the GCS stored
    configuration:

        - Bucket in :py:data:`CONFIG_BUCKET_NAME_ENV_VAR`
        - Object path: :py:data:`CONFIG_OBJECT_PATH_ENV_VAR`
    Returns:
    """
    bucket_name = os.getenv(CONFIG_BUCKET_NAME_ENV_VAR)
    object_path = os.getenv(CONFIG_OBJECT_PATH_ENV_VAR)
    try:
        config_json = gcs.read_object(bucket_name=bucket_name, object_path=object_path, warn_read_failure=True)
    except Exception as err:
        raise RuntimeError(
            f"Could not read config object in bucket <{bucket_name}> " f"and object <{object_path}>. " f"Error: {err}"
        ) from err
    try:
        result = config.Config.from_json(config_json)
    except Exception as err:
        raise RuntimeError(
            f"Could not extract <{config.Config.__name__}> " f"from JSON content: <{config_json}>. " f"Error: {err}"
        ) from err
    try:
        result = resolve_config.consolidate_config(result, raise_if_failed=False)
    except Exception as err:
        raise RuntimeError(
            f"Could not consolidate Pub/Sub topics on <{result}>. "
            f"Specifically: <{result.topic_to_pubsub_gcs}>. "
            f"Error: {err}"
        ) from err
    return result


#############
# Cloud Run #
#############


def configuration() -> str:
    """To be declared as an API entry point for configuration.
    E.g.::
        @MAIN_BP.route("/config", methods=["GET"])
        def configuration() -> str:
            return cloud_run.configuration()
    """
    _LOGGER.debug("Request data: <%s>(%s)", flask.request.data, type(flask.request.data))
    _LOGGER.info("Calling %s", configuration.__name__)
    try:
        result = flask.jsonify(read_configuration().as_dict())
    except Exception as err:  # pylint: disable=broad-except
        msg = f"Could get configuration. Error: {err}"
        _LOGGER.exception(msg)
        result = flask.jsonify({"error": msg})
    return result


async def handle_request(
    *,
    what: str,
    async_kwargs_fn: Callable[[flask.Request], Dict[str, Any]],
    async_fn: Callable[[Dict[str, Any]], None],
) -> str:
    kwargs, err_msg = await _kwargs_from_flask_request(async_kwargs_fn)
    if not err_msg:
        response, err_msg = await _call_and_respond(
            what=what,
            async_fn=async_fn,
            kwargs=kwargs,
        )
    if err_msg:
        result = flask.jsonify(error=err_msg)
    else:
        result = flask.jsonify(response=response)
    return result


async def _kwargs_from_flask_request(
    async_kwargs_fn: Callable[[flask.Request], Dict[str, Any]]
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Will call the argument with the current instance of
    :py:class:`flask.Request`. It is expected that the output is
    :py:class:`dict` corresponding to the ``kwargs`` needed by the
    corresponding later call. This function is provided so that all errors are
    properly handled.

    Args:
        async_kwargs_fn:

    Returns:
    """
    kwargs = None
    err_msg = None
    try:
        kwargs = await async_kwargs_fn(flask.request)
    except Exception as err:  # pylint: disable=broad-except
        err_msg = (
            f"Could not create kwargs from request <{flask.request}> "
            f"using <{async_kwargs_fn.__name__}>. "
            f"Error: {err}"
        )
        _LOGGER.exception(err_msg)
    return kwargs, err_msg


async def _call_and_respond(
    *,
    what: str,
    async_fn: Callable[[Dict[str, Any]], None],
    kwargs: Dict[str, Any],
) -> Tuple[Any, Optional[str]]:
    """This function will call your function in ``async_fn`` that is responding
    to a REST API call. It is here so that all error handling is done properly.

    Args:
        what:
        async_fn:
        kwargs:
        err_msg:

    Returns:
    """
    _LOGGER.debug("Request data: <%s>(%s)", flask.request.data, type(flask.request.data))
    result = None
    err_msg = None
    try:
        _LOGGER.info("Calling %s through <%s> with <%s>", what, async_fn.__name__, kwargs)
        result = await async_fn(**kwargs)
    except Exception as err:  # pylint: disable=broad-except
        err_msg = (
            f"Could not process {what} using <{async_fn.__name__}> " f"and arguments: <{kwargs}>. " f"Error: {err}"
        )
        _LOGGER.exception(err_msg)
    return result, err_msg


def main():
    """To test::

    export CONFIG_BUCKET_NAME=yaas_cache
    export CONFIG_OBJECT_PATH=yaas_gcp-scaler-scheduler_service-common.cfg
    python -m yaas_flask.cloud_run
    """
    port = int(os.getenv("PORT")) if os.getenv("PORT") else 8080
    create_app().run(host="127.0.0.1", port=port, debug=True)
