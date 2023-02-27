# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods,
# type: ignore
from yaas_common import const
from yaas_common.dto import command, request

# update secrets
# pylint: disable=line-too-long
TEST_COMMAND_UPDATE_CALENDAR_CREDENTIALS_SECRET: command.CommandUpdateCalendarCredentialsSecret = command.CommandUpdateCalendarCredentialsSecret(
    type=const.CMD_TYPE_UPDATE_CALENDAR_CREDENTIALS_SECRET
)
# pylint: enable=line-too-long
# update cache
_TEST_COMMAND_UPDATE_CALENDAR_CACHE_RANGE: request.Range = request.Range(
    period_minutes=3600, now_diff_minutes=30
)
TEST_COMMAND_UPDATE_CALENDAR_CACHE: command.CommandUpdateCalendarCache = (
    command.CommandUpdateCalendarCache(
        type=const.CMD_TYPE_UPDATE_CALENDAR_CACHE,
        range=_TEST_COMMAND_UPDATE_CALENDAR_CACHE_RANGE,
    )
)
# send requests
_TEST_COMMAND_SEND_SCALING_REQUESTS_RANGE: request.Range = request.Range(
    period_minutes=40, now_diff_minutes=-10
)
TEST_COMMAND_SEND_SCALING_REQUESTS: command.CommandSendScalingRequests = (
    command.CommandSendScalingRequests(
        type=const.CMD_TYPE_SEND_SCALING_REQUESTS,
        range=_TEST_COMMAND_SEND_SCALING_REQUESTS_RANGE,
    )
)
