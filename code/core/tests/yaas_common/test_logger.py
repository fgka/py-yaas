# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,protected-access
# pylint: disable=attribute-defined-outside-init,invalid-name
# type: ignore
import io
import logging
import sys

from yaas_common import logger


class TestOneLineExceptionFormatter:
    def setup_method(self):
        self.instance = logger.OneLineExceptionFormatter(logger._LOGGER_FORMAT)

    def test_ctor_ok_empty_format(self):
        assert logger.OneLineExceptionFormatter() is not None

    def test_ctor_ok(self):
        assert logger.OneLineExceptionFormatter(logger._LOGGER_FORMAT) is not None

    def test_formatException_ok(self):
        # Given
        exc_info = self._exec_info()
        # When
        result = self.instance.formatException(exc_info)
        # Then
        assert isinstance(result, str)
        assert len(result.split("\n")) == 1
        assert ZeroDivisionError.__name__ in result

    @staticmethod
    def _exec_info() -> tuple:
        result = None
        try:
            _ = 1 / 0
        except Exception:  # pylint: disable=broad-except
            result = sys.exc_info()
        # check result
        assert result[0] == ZeroDivisionError
        #
        return result

    def test_format_ok(self):
        # Given
        exc_info = self._exec_info()
        record = logging.LogRecord(
            name=__name__,
            level=logging.ERROR,
            pathname=__file__,
            lineno=123,
            msg="test_message",
            args=None,
            exc_info=exc_info,
        )
        # When
        result = self.instance.format(record)
        assert isinstance(result, str)
        assert len(result.split("\n")) == 1
        assert ZeroDivisionError.__name__ in result


def test_logger_exception():
    # Given
    obj = logger.get(__name__)
    stream = io.StringIO()
    obj.addHandler(logger._create_stream_handler(logging.DEBUG, logger.LogFilter(level_range=(0, 10000)), stream))
    # When
    try:
        _ = 1 / 0
    except Exception as err:  # pylint: disable=broad-except
        obj.exception("Some error: %s", err)
    # Then
    stream.seek(0)
    result = stream.read()
    assert isinstance(result, str)
    lines = result.strip().split("\n")
    assert len(lines) == 1
    assert ZeroDivisionError.__name__ in result
