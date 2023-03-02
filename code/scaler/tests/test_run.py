# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# pylint: disable=duplicate-code
# type: ignore
from typing import Any, Dict, List, Optional, Tuple
import pytest

from yaas_gcp import cloud_run_const
from yaas_scaler import run

from tests import common

_CALLED: Dict[str, bool] = {}


class TestCloudRunScalingCommand:
    def test_ctor_ok(self):
        # Given
        for param in run.CloudRunCommandType:
            # When
            obj = run.CloudRunScalingCommand(parameter=param.value, target=123)
            # Then
            assert isinstance(obj, run.CloudRunScalingCommand)
            assert obj.parameter == param.value

    @pytest.mark.parametrize(
        "parameter,target,exception",
        [
            (run.CloudRunCommandType.MIN_INSTANCES.value + "_NOT", 123, TypeError),
            (run.CloudRunCommandType.MIN_INSTANCES.value, "123", TypeError),
            (run.CloudRunCommandType.MIN_INSTANCES.value, -1, ValueError),
        ],
    )
    def test_ctor_nok(self, parameter: str, target: int, exception: Any):
        # Given/When/Then
        with pytest.raises(exception):
            run.CloudRunScalingCommand(parameter=parameter, target=target)

    def test_from_command_str_ok(self):
        # Given
        for param in run.CloudRunCommandType:
            cmd_str = f"{param.value} 123"
            # When
            obj = run.CloudRunScalingCommand.from_command_str(cmd_str)
            # Then
            assert isinstance(obj, run.CloudRunScalingCommand)
            assert obj.parameter == param.value


_TEST_CLOUD_RUN_RESOURCE_STR: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)


def _create_cloud_run_scaling_definition(
    *,
    resource: str = _TEST_CLOUD_RUN_RESOURCE_STR,
    parameter: run.CloudRunCommandType = run.CloudRunCommandType.MAX_INSTANCES,
    target: int = 123,
    timestamp_utc: int = 321,
) -> run.CloudRunScalingDefinition:
    command = run.CloudRunScalingCommand(parameter=parameter.value, target=target)
    return run.CloudRunScalingDefinition(
        resource=resource, command=command, timestamp_utc=timestamp_utc
    )


class TestCloudRunScalingDefinition:
    def test_ctor_ok(self):
        # Given
        resource = _TEST_CLOUD_RUN_RESOURCE_STR
        # When
        obj = _create_cloud_run_scaling_definition(resource=resource)
        # Then
        assert isinstance(obj, run.CloudRunScalingDefinition)
        assert obj.resource == resource

    def test_ctor_nok_wrong_resource(self):
        # Given
        resource = "NOT_" + _TEST_CLOUD_RUN_RESOURCE_STR
        command = run.CloudRunScalingCommand(
            parameter=run.CloudRunCommandType.MIN_INSTANCES.value, target=123
        )
        # When/Then
        with pytest.raises(ValueError):
            run.CloudRunScalingDefinition(
                resource=resource, command=command, timestamp_utc=321
            )

    def test_from_request_ok(self):
        # Given
        req = common.create_scale_request(
            resource=_TEST_CLOUD_RUN_RESOURCE_STR,
            command=f"{run.CloudRunCommandType.CONCURRENCY.value} 123",
        )
        # When
        obj = run.CloudRunScalingDefinition.from_request(req)
        # Then
        assert isinstance(obj, run.CloudRunScalingDefinition)
        assert obj.resource == req.resource


class TestCloudRunScaler:
    def setup(self):
        self.definition = [
            _create_cloud_run_scaling_definition(parameter=param, target=ndx)
            for ndx, param in enumerate(run.CloudRunCommandType)
        ]

    def test_ctor_ok(self):
        # Given/When
        obj = run.CloudRunScaler(*self.definition)
        # Then
        assert isinstance(obj, run.CloudRunScaler)

    def test_from_request_ok(self):
        # Given
        req = common.create_scale_request(
            resource=_TEST_CLOUD_RUN_RESOURCE_STR,
            command=f"{run.CloudRunCommandType.CONCURRENCY.value} 123",
        )
        # When
        obj = run.CloudRunScaler.from_request(req)
        # Then
        assert isinstance(obj, run.CloudRunScaler)
        assert obj.resource == req.resource

    @pytest.mark.parametrize(
        "field,expected",
        [
            (
                run.CloudRunCommandType.MIN_INSTANCES.value,
                cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MIN_INSTANCES_PARAM,
            ),
            (
                run.CloudRunCommandType.MAX_INSTANCES.value,
                cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MAX_INSTANCES_PARAM,
            ),
            (
                run.CloudRunCommandType.CONCURRENCY.value,
                cloud_run_const.CLOUD_RUN_SERVICE_SCALING_CONCURRENCY_PARAM,
            ),
            (
                None,
                None,
            ),
            (
                123,
                None,
            ),
            (
                run.CloudRunCommandType.CONCURRENCY.value + "_NOT",
                None,
            ),
        ],
    )
    def test__get_enact_path_value_ok(self, field: str, expected: str):
        # Given/When
        result = run.CloudRunScaler._get_enact_path_value(
            resource="resource", field=field, target="target"
        )
        # Then
        assert result == expected

    def test__get_enact_path_value_ok_all(self):
        # Given
        for cmd_type in run.CloudRunCommandType:
            # When
            result = run.CloudRunScaler._get_enact_path_value(
                resource="resource", field=cmd_type.value, target="target"
            )
            # Then
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_enact_ok(self, monkeypatch):
        # Given
        update_name = None
        update_path_value_lst = None
        can_be_value = None

        async def mocked_update_service(
            *, name: str, path_value_lst: List[Tuple[str, Optional[Any]]]
        ) -> Any:
            nonlocal update_name, update_path_value_lst
            update_name = name
            update_path_value_lst = path_value_lst

        async def mocked_can_be_deployed(value: str) -> Tuple[bool, str]:
            nonlocal can_be_value
            can_be_value = value
            return True, None

        monkeypatch.setattr(
            run.cloud_run,
            run.cloud_run.update_service.__name__,
            mocked_update_service,
        )
        monkeypatch.setattr(
            run.cloud_run,
            run.cloud_run.can_be_deployed.__name__,
            mocked_can_be_deployed,
        )
        obj = run.CloudRunScaler(*self.definition)
        # When
        result = await obj.enact()
        # Then
        assert result
        assert can_be_value == obj.resource
        assert update_name == obj.resource
        assert len(update_path_value_lst) == len(self.definition)


def _expected_cloud_run_update_path(param: run.CloudRunCommandType) -> str:
    if param == run.CloudRunCommandType.MIN_INSTANCES:
        return cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MIN_INSTANCES_PARAM
    if param == run.CloudRunCommandType.MAX_INSTANCES:
        return cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MAX_INSTANCES_PARAM
    if param == run.CloudRunCommandType.CONCURRENCY:
        return cloud_run_const.CLOUD_RUN_SERVICE_SCALING_CONCURRENCY_PARAM
    return None
