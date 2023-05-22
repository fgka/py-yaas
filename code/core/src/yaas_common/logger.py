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
import io
import logging
import os
import sys
from typing import Optional, Tuple, Union

from google.cloud import logging as cloud_logging
from google.cloud.logging import handlers as cloud_handlers

_CLOUD_LOGGING_CLIENT: cloud_logging.Client = None

try:
    _CLOUD_LOGGING_CLIENT = cloud_logging.Client()
except Exception as err:  # pylint: disable=broad-except
    print(f"Could not start Google Client logging. Ignoring. Error: {err}")


LOG_LEVEL_ENV_VAR_NAME: str = "LOG_LEVEL"  # DEBUG or WARNING, etc
_DEFAULT_LOG_LEVEL: int = logging.INFO
_LOGGER_FORMAT: str = "[%(asctime)s %(filename)s.%(funcName)s:%(lineno)s]%(levelname)s: %(message)s"
_STD_OUT_LEVELS: Tuple[int, int] = (0, logging.INFO)
_STD_ERR_LEVELS: Tuple[int, int] = (logging.INFO + 1, logging.CRITICAL + 1000)


class OneLineExceptionFormatter(logging.Formatter):
    """
    Source: https://stackoverflow.com/questions/28180159/how-do-i-can-format-exception-stacktraces-in-python-logging
    """

    def formatException(self, ei: tuple) -> str:
        """Formats an exception"""
        result = super().formatException(ei)
        return repr(result)

    def format(self, record: logging.LogRecord) -> str:
        """Formats a log record"""
        result = super().format(record)
        if record.exc_text:
            result = result.replace("\n", "|")
        return result


class LogFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Filter log messages based on log-level"""

    def __init__(self, *args, level_range: Tuple[int] = _STD_OUT_LEVELS, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(level_range, tuple) and len(level_range) == 2:
            raise TypeError(f"Level range must be a pair. Got '{level_range}'({type(level_range)})")
        self._level_min = level_range[0]
        self._level_max = level_range[1]

    def filter(self, record: logging.LogRecord) -> bool:
        return self._level_min <= record.levelno <= self._level_max


class StdOutFilter(LogFilter):  # pylint: disable=too-few-public-methods
    """Log filter to be used to send messages to standard out"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, level_range=_STD_OUT_LEVELS, **kwargs)


class StdErrFilter(LogFilter):  # pylint: disable=too-few-public-methods
    """Log filter to be used to send messages to standard err"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, level_range=_STD_ERR_LEVELS, **kwargs)


def get(name: str, *, level: Optional[Union[str, int]] = None) -> logging.Logger:
    """Creates a :py:class:`logging.Logger` setting the log level based on the
    following priority:

    - argument `level`.
    - environment variable :py:data:`LOG_LEVEL_ENV_VAR_NAME`.
    - default value in: :py:data:`_DEFAULT_LOG_LEVEL`.

    Args:
        name: logger name.
        level: default logging level.

    Returns:
        :py:cls:`logging.Logger` instance.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Name must be a non-empty string. Got: '{name}'({type(name)})")
    name = name.strip()
    level = _log_level(level)
    logging.basicConfig(level=level)
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
    result.addHandler(_create_stdout_stream_handler(level))
    result.addHandler(_create_stderr_stream_handler(level))
    if _CLOUD_LOGGING_CLIENT is not None:
        result.addHandler(
            _setup_handler(
                cloud_handlers.CloudLoggingHandler(_CLOUD_LOGGING_CLIENT),
                level,
            )
        )
    return result


def _create_stdout_stream_handler(level: int) -> logging.StreamHandler:
    return _create_stream_handler(level, StdOutFilter(), sys.stdout)


def _create_stream_handler(level: int, log_filter: logging.Filter, stream: io.TextIOWrapper) -> logging.StreamHandler:
    result = _setup_handler(logging.StreamHandler(stream), level)
    result.addFilter(log_filter)
    return result


def _create_stderr_stream_handler(level: int) -> logging.StreamHandler:
    return _create_stream_handler(level, StdErrFilter(), sys.stderr)


def _setup_handler(value: logging.Handler, level: int, format_str: Optional[str] = _LOGGER_FORMAT) -> logging.Handler:
    value.setLevel(level)
    value.setFormatter(OneLineExceptionFormatter(format_str))
    return value
