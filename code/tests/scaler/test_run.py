# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Dict, Optional, Tuple
import pytest

from yaas.gcp import cloud_run_const
from yaas.scaler import run

from tests import common

_CALLED: Dict[str, bool] = {}


class TestCloudRunScalingCommand:
    def test_ctor_ok(self):
        # Given
        for param in run.CloudRunCommandTypes:
            # When
            obj = run.CloudRunScalingCommand(parameter=param.value, target=123)
            # Then
            assert obj is not None

    @pytest.mark.parametrize(
        "parameter,target,exception",
        [
            (run.CloudRunCommandTypes.MIN_INSTANCES.value + "_NOT", 123, TypeError),
            (run.CloudRunCommandTypes.MIN_INSTANCES.value, "123", TypeError),
            (run.CloudRunCommandTypes.MIN_INSTANCES.value, -1, ValueError),
        ],
    )
    def test_ctor_nok(self, parameter: str, target: int, exception: Any):
        # Given/When/Then
        with pytest.raises(exception):
            run.CloudRunScalingCommand(parameter=parameter, target=target)

    def test_from_command_str_ok(self):
        # Given
        for param in run.CloudRunCommandTypes:
            cmd_str = f"{param.value} 123"
            # When
            obj = run.CloudRunScalingCommand.from_command_str(cmd_str)
            # Then
            assert obj is not None


_TEST_CLOUD_RUN_RESOURCE_STR: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)


def _create_cloud_run_scaling_definition(
    *,
    resource: str = _TEST_CLOUD_RUN_RESOURCE_STR,
    parameter: run.CloudRunCommandTypes = run.CloudRunCommandTypes.MAX_INSTANCES,
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
        assert obj is not None
        assert obj.resource == _TEST_CLOUD_RUN_RESOURCE_STR

    def test_ctor_nok_wrong_resource(self):
        # Given
        resource = "NOT_" + _TEST_CLOUD_RUN_RESOURCE_STR
        command = run.CloudRunScalingCommand(
            parameter=run.CloudRunCommandTypes.MIN_INSTANCES.value, target=123
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
            command=f"{run.CloudRunCommandTypes.CONCURRENCY.value} 123",
        )
        # When
        obj = run.CloudRunScalingDefinition.from_request(req)
        # Then
        assert obj is not None
        assert obj.resource == _TEST_CLOUD_RUN_RESOURCE_STR


class TestCloudRunScaler:
    def test_ctor_ok(self):
        # Given
        definition = _create_cloud_run_scaling_definition()
        # When
        obj = run.CloudRunScaler(definition=definition)
        # Then
        assert obj is not None

    def test_from_request_ok(self):
        # Given
        req = common.create_scale_request(
            resource=_TEST_CLOUD_RUN_RESOURCE_STR,
            command=f"{run.CloudRunCommandTypes.CONCURRENCY.value} 123",
        )
        # When
        obj = run.CloudRunScaler.from_request(req)
        # Then
        assert obj is not None

    @pytest.mark.asyncio
    async def test_enact_ok(self, monkeypatch):
        # Given
        update_name = None
        update_path = None
        update_value = None
        can_be_value = None

        async def mocked_update_service(
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
            run.cloud_run,
            run.cloud_run.update_service.__name__,
            mocked_update_service,
        )
        monkeypatch.setattr(
            run.cloud_run,
            run.cloud_run.can_be_deployed.__name__,
            mocked_can_be_deployed,
        )
        target = 13
        for param in run.CloudRunCommandTypes:
            exp_path = _expected_cloud_run_update_path(param)
            definition = _create_cloud_run_scaling_definition(
                parameter=param, target=target
            )
            obj = run.CloudRunScaler(definition)
            # When
            result = await obj.enact()
            # Then
            assert result
            assert can_be_value == obj.definition.resource
            assert update_name == obj.definition.resource
            assert update_path == exp_path
            assert update_value == target


def _expected_cloud_run_update_path(param: run.CloudRunCommandTypes) -> str:
    if param == run.CloudRunCommandTypes.MIN_INSTANCES:
        return cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MIN_INSTANCES_PARAM
    if param == run.CloudRunCommandTypes.MAX_INSTANCES:
        return cloud_run_const.CLOUD_RUN_SERVICE_SCALING_MAX_INSTANCES_PARAM
    if param == run.CloudRunCommandTypes.CONCURRENCY:
        return cloud_run_const.CLOUD_RUN_SERVICE_SCALING_CONCURRENCY_PARAM
    return None
