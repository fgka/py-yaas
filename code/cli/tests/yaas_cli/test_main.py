# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,redefined-outer-name
# type: ignore
import pytest
from click import testing

from yaas_cli import main


@pytest.fixture(scope="module")
def cli_runner() -> testing.CliRunner:
    return testing.CliRunner()


def test_main_ok(cli_runner):
    result = cli_runner.invoke(main.cli, ["--help"])
    assert result
    assert result.exit_code == 0
