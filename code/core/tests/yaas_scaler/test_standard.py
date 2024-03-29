# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,protected-access,attribute-defined-outside-init
# type: ignore
import pytest

from tests import common
from yaas_common import request
from yaas_scaler import resource_name_parser, run, scaling, sql, standard

_TEST_CLOUD_FUNCTION_RESOURCE_STR: str = "projects/my-project-123/locations/my-location-123/functions/my-function-123"
_TEST_CLOUD_RUN_RESOURCE_STR: str = "projects/my-project-123/locations/my-location-123/services/my-service-123"
_TEST_DEFAULT_CLOUD_RUN_COMMAND_STR: str = f"{run.CloudRunCommandType.CONCURRENCY.value} 123"
_TEST_CLOUD_SQL_RESOURCE_STR: str = "my-project-123:my-location-123:my-instance-123"
_TEST_DEFAULT_CLOUD_SQL_COMMAND_STR: str = f"{sql.CloudSqlCommandType.INSTANCE_TYPE.value} db-custom-1-3480"


def _create_request(
    *,
    topic: str = standard.StandardCategoryType.default().value,
    resource: str = _TEST_CLOUD_RUN_RESOURCE_STR,
    command: str = _TEST_DEFAULT_CLOUD_RUN_COMMAND_STR,
) -> request.ScaleRequest:
    return common.create_scale_request(
        topic=topic,
        resource=resource,
        command=command,
    )


class TestStandardScalingCommandParser:
    def setup_method(self):
        self.obj = standard.StandardScalingCommandParser()

    @pytest.mark.parametrize(
        "resource,command",
        [
            (_TEST_CLOUD_RUN_RESOURCE_STR, _TEST_DEFAULT_CLOUD_RUN_COMMAND_STR),
            (_TEST_CLOUD_SQL_RESOURCE_STR, _TEST_DEFAULT_CLOUD_SQL_COMMAND_STR),
        ],
    )
    def test_scaler_ok(self, resource: str, command: str):
        for topic in standard.StandardCategoryType:
            # Given
            req = _create_request(topic=topic.value, resource=resource, command=command)
            # When
            result = self.obj.scaler(req)
            # Then
            assert result is not None

    def test_scaler_nok_wrong_topic(self):
        for topic in standard.StandardCategoryType:
            # Given
            req = _create_request(topic=topic.value + "_NOT")
            # When/Then
            with pytest.raises(ValueError):
                self.obj.scaler(req)

    def test_scaler_nok_wrong_resource(self):
        # Given
        req = _create_request(resource=_TEST_CLOUD_FUNCTION_RESOURCE_STR)
        # When/Then
        with pytest.raises(ValueError):
            self.obj.scaler(req)

    @pytest.mark.parametrize(
        "value",
        [
            request.ScaleRequest(
                topic="standard",
                resource="locations/europe-west3/namespaces/yaas-test/services/integ-test",
                command="min_instances 10",
                timestamp_utc=123,
                original_json_event=None,
            ),
            request.ScaleRequest(
                topic="standard",
                resource="yaas-test:europe-west3:integ-test",
                command="instance_type db-custom-2-3840",
                timestamp_utc=123,
                original_json_event=None,
            ),
        ],
    )
    def test__scaling_definition_from_request_ok(self, value: request.ScaleRequest):
        # Given/When
        result = self.obj._scaling_definition_from_request(value)
        # Then
        assert isinstance(result, scaling.ScalingDefinition)
        _, canonical_resource = resource_name_parser.canonical_resource_type_and_name(value.resource)
        assert result.resource == canonical_resource
