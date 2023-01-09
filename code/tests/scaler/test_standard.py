# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import pytest

from yaas.dto import request
from yaas.scaler import run, standard

from tests import common


_TEST_CLOUD_RUN_RESOURCE_STR: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)
_TEST_CLOUD_FUNCTION_RESOURCE_STR: str = (
    "projects/my-project-123/locations/my-location-123/functions/my-function-123"
)
_TEST_DEFAULT_CLOUD_RUN_COMMAND_STR: str = (
    f"{run.CloudRunCommandTypes.CONCURRENCY.value} 123"
)


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

    def test_scaler_ok(self):
        for topic in standard.StandardCategoryType:
            # Given
            req = _create_request(topic=topic.value)
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
        with pytest.raises(TypeError):
            self.obj.scaler(req)
