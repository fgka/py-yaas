# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pytest

from yaas_command import command_parser
from yaas_common import command

from tests import command_test_data


@pytest.mark.parametrize(
    "value",
    [
        command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CREDENTIALS_SECRET,
        command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CACHE,
        command_test_data.TEST_COMMAND_SEND_SCALING_REQUESTS,
    ],
)
def test_to_command_ok(value: command.CommandBase):
    # Given/When
    result = command_parser.to_command(value.as_dict())
    # Then
    for key in result.as_dict():
        assert getattr(value, key) == getattr(result, key)


def test_to_command_ok_supports_all_commands():
    # Given
    tested = set()
    available_cmds = [
        command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CREDENTIALS_SECRET,
        command_test_data.TEST_COMMAND_UPDATE_CALENDAR_CACHE,
        command_test_data.TEST_COMMAND_SEND_SCALING_REQUESTS,
    ]
    # When
    for cmd in available_cmds:
        result = command_parser.to_command(cmd.as_dict())
        assert isinstance(result, command.CommandBase)
        tested.add(command.CommandType.from_str(result.type))
    # Then
    assert set(command.CommandType) == tested
