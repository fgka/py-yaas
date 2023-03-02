# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Logger definition, get all loggers from this module::
    from yaas_gcp-scaler-scheduler_service-common import logger
    _LOGGER = logger.get(__name__)

It also automatically install `Cloud Logging`_.

.. _Cloud Logging: https://cloud.google.com/python/docs/reference/logging/latest/handlers-cloud-logging#google.cloud.logging_v2.handlers.handlers.CloudLoggingHandler
"""
# pylint: enable=line-too-long
import logging
import os
from typing import Optional, Union

from google.cloud import logging as cloud_logging
from google.cloud.logging import handlers as cloud_handlers

_CLOUD_LOGGING_CLIENT: cloud_logging.Client = None

try:
    _CLOUD_LOGGING_CLIENT = cloud_logging.Client()
except Exception as err:  # pylint: disable=broad-except
    print(f"Could not start Google Client logging. Ignoring. Error: {err}")


LOG_LEVEL_ENV_VAR_NAME: str = "LOG_LEVEL"  # DEBUG or WARNING, etc
_DEFAULT_LOG_LEVEL: int = logging.INFO
_LOGGER_FORMAT: str = (
    "[%(asctime)s %(filename)s.%(funcName)s:%(lineno)s]%(levelname)s: %(message)s"
)


def get(name: str, *, level: Optional[Union[str, int]] = None) -> logging.Logger:
    """
    Creates a :py:class:`logging.Logger` setting the log level based on the following priority:
    - argument `level`;
    - environment variable :py:data:`LOG_LEVEL_ENV_VAR_NAME`;
    - default value in: :py:data:`_DEFAULT_LOG_LEVEL`.

    Args:
        name: logger name.
        level: default logging level.

    Returns:
        :py:cls:`logging.Logger` instance.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            f"Name must be a non-empty string. Got: <{name}>({type(name)})"
        )
    name = name.strip()
    level = _log_level(level)
    logging.basicConfig(level=level, format=_LOGGER_FORMAT)
    logging.debug("Set log level for %s to %d", name, level)
    return _create_logger(name, level)


def _log_level(level: Optional[Union[str, int]]) -> int:
    result = None
    # argument
    if isinstance(level, int):
        result = level
    if isinstance(level, str):
        result = getattr(logging, level)
    # env var
    if result is None:
        level_str = os.environ.get(LOG_LEVEL_ENV_VAR_NAME)
        if level_str:
            result = getattr(logging, level_str)
    # default
    if result is None:
        result = _DEFAULT_LOG_LEVEL
    return result


def _create_logger(name: str, level: int) -> logging.Logger:
    result = logging.getLogger(name.strip())
    result.setLevel(level)
    if level == logging.DEBUG:
        formatter = logging.Formatter(_LOGGER_FORMAT)
        result.addHandler(_setup_handler(logging.StreamHandler(), level, formatter))
        if _CLOUD_LOGGING_CLIENT is not None:
            result.addHandler(
                _setup_handler(
                    cloud_handlers.CloudLoggingHandler(_CLOUD_LOGGING_CLIENT),
                    level,
                    formatter,
                )
            )
    return result


def _setup_handler(
    value: logging.Handler, level: int, formatter: logging.Formatter
) -> logging.Handler:
    value.setLevel(level)
    value.setFormatter(formatter)
    return value
