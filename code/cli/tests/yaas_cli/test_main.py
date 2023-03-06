# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring
# type: ignore
import pytest
from click import testing

from yaas_cli import main


@pytest.fixture(scope="module")
def click_runner() -> testing.CliRunner:
    return testing.CliRunner()


def test_main_ok(click_runner):
    result = click_runner.invoke(main.cli, ["--help"])
    assert result
    assert result.exit_code == 0
