# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# pylint: disable=duplicate-code
# type: ignore
from typing import Any, Dict, Optional, Tuple
import pytest

from yaas.gcp import cloud_sql_const
from yaas.scaler import sql

from tests import common

_CALLED: Dict[str, bool] = {}


class TestCloudSqlScalingCommand:
    def test_ctor_ok(self):
        # Given
        for param in sql.CloudSqlCommandType:
            # When
            obj = sql.CloudSqlScalingCommand(parameter=param.value, target="value")
            # Then
            assert obj is not None

    @pytest.mark.parametrize(
        "parameter,target,exception",
        [
            (sql.CloudSqlCommandType.INSTANCE_TYPE.value + "_NOT", "value", TypeError),
            (sql.CloudSqlCommandType.INSTANCE_TYPE.value, 123, TypeError),
            (sql.CloudSqlCommandType.INSTANCE_TYPE.value, "", ValueError),
        ],
    )
    def test_ctor_nok(self, parameter: str, target: int, exception: Any):
        # Given/When/Then
        with pytest.raises(exception):
            sql.CloudSqlScalingCommand(parameter=parameter, target=target)

    def test_from_command_str_ok(self):
        # Given
        for param in sql.CloudSqlCommandType:
            cmd_str = f"{param.value} value"
            # When
            obj = sql.CloudSqlScalingCommand.from_command_str(cmd_str)
            # Then
            assert obj is not None


_TEST_CLOUD_SQL_RESOURCE_STR: str = "my-project-123:my-location-123:my-instance-123"
_TEST_CLOUD_SQL_INSTANCE_TYPE: str = "db-custom-1-10"


def _create_cloud_sql_scaling_definition(
    *,
    resource: str = _TEST_CLOUD_SQL_RESOURCE_STR,
    parameter: sql.CloudSqlCommandType = sql.CloudSqlCommandType.INSTANCE_TYPE,
    target: str = _TEST_CLOUD_SQL_INSTANCE_TYPE,
    timestamp_utc: int = 321,
) -> sql.CloudSqlScalingDefinition:
    command = sql.CloudSqlScalingCommand(parameter=parameter.value, target=target)
    return sql.CloudSqlScalingDefinition(
        resource=resource, command=command, timestamp_utc=timestamp_utc
    )


_TEST_CLOUD_SQL_COMMAND_STR: str = (
    f"{sql.CloudSqlCommandType.INSTANCE_TYPE.value} {_TEST_CLOUD_SQL_INSTANCE_TYPE}"
)


class TestCloudRunScalingDefinition:
    def test_ctor_ok(self):
        # Given
        resource = _TEST_CLOUD_SQL_RESOURCE_STR
        # When
        obj = _create_cloud_sql_scaling_definition(resource=resource)
        # Then
        assert obj is not None
        assert obj.resource == _TEST_CLOUD_SQL_RESOURCE_STR

    def test_ctor_nok_wrong_resource(self):
        # Given
        resource = "NOT:" + _TEST_CLOUD_SQL_RESOURCE_STR
        command = sql.CloudSqlScalingCommand(
            parameter=sql.CloudSqlCommandType.INSTANCE_TYPE.value,
            target=_TEST_CLOUD_SQL_INSTANCE_TYPE,
        )
        # When/Then
        with pytest.raises(ValueError):
            sql.CloudSqlScalingDefinition(
                resource=resource, command=command, timestamp_utc=321
            )

    def test_from_request_ok(self):
        # Given
        req = common.create_scale_request(
            resource=_TEST_CLOUD_SQL_RESOURCE_STR,
            command=_TEST_CLOUD_SQL_COMMAND_STR,
        )
        # When
        obj = sql.CloudSqlScalingDefinition.from_request(req)
        # Then
        assert obj is not None
        assert obj.resource == _TEST_CLOUD_SQL_RESOURCE_STR


class TestCloudRunScaler:
    def test_ctor_ok(self):
        # Given
        definition = _create_cloud_sql_scaling_definition()
        # When
        obj = sql.CloudSqlScaler(definition=definition)
        # Then
        assert obj is not None

    def test_from_request_ok(self):
        # Given
        req = common.create_scale_request(
            resource=_TEST_CLOUD_SQL_RESOURCE_STR,
            command=_TEST_CLOUD_SQL_COMMAND_STR,
        )
        # When
        obj = sql.CloudSqlScaler.from_request(req)
        # Then
        assert obj is not None

    @pytest.mark.asyncio
    async def test_enact_ok(self, monkeypatch):
        # Given
        update_name = None
        update_path = None
        update_value = None
        can_be_value = None

        async def mocked_update_instance(
            *, name: str, path: str, value: Optional[Any]
        ) -> Any:
            nonlocal update_name, update_path, update_value
            update_name = name
            update_path = path
            update_value = value

        async def mocked_can_be_deployed(value: str) -> Tuple[bool, str]:
            nonlocal can_be_value
            can_be_value = value
            return True, None

        monkeypatch.setattr(
            sql.cloud_sql,
            sql.cloud_sql.update_instance.__name__,
            mocked_update_instance,
        )
        monkeypatch.setattr(
            sql.cloud_sql,
            sql.cloud_sql.can_be_deployed.__name__,
            mocked_can_be_deployed,
        )
        target = _TEST_CLOUD_SQL_INSTANCE_TYPE
        for param in sql.CloudSqlCommandType:
            exp_path = _expected_cloud_run_update_path(param)
            definition = _create_cloud_sql_scaling_definition(
                parameter=param, target=target
            )
            obj = sql.CloudSqlScaler(definition)
            # When
            result = await obj.enact()
            # Then
            assert result
            assert can_be_value == obj.definition.resource
            assert update_name == obj.definition.resource
            assert update_path == exp_path
            assert update_value == target


def _expected_cloud_run_update_path(param: sql.CloudSqlCommandType) -> str:
    if param == sql.CloudSqlCommandType.INSTANCE_TYPE:
        return cloud_sql_const.CLOUD_SQL_SERVICE_SCALING_INSTANCE_TYPE_PARAM
    return None
