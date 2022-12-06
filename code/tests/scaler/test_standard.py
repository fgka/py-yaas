# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,no-self-use,using-constant-test
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# pylint: disable=redefined-builtin
# type: ignore
from typing import Any, Dict, Optional, Tuple
import pytest

from yaas.dto import request
from yaas.gcp import cloud_run_const
from yaas.scaler import run, standard


_TEST_CLOUD_RUN_RESOURCE_STR: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)
_TEST_CLOUD_FUNCTION_RESOURCE_STR: str = (
    "projects/my-project-123/locations/my-location-123/functions/my-function-123"
)
_TEST_DEFAULT_CLOUD_RUN_COMMAND_STR: str = f"{run.CloudRunCommandTypes.CONCURRENCY.value} 123"


def _create_request(*, topic: str = standard.StandardCategoryType.default().value,
                    resource: str = _TEST_CLOUD_RUN_RESOURCE_STR,
                    command: str = _TEST_DEFAULT_CLOUD_RUN_COMMAND_STR) -> request.ScaleRequest:
    return request.ScaleRequest(
        topic=topic,
        resource=resource,
        command=command,
    )


class TestStandardScalingCommandParser:
    def test_ctor_ok(self):
        for topic in standard.StandardCategoryType:
            # Given
            req = _create_request(topic=topic.value)
            # When
            obj = standard.StandardScalingCommandParser(req)
            # Then
            assert obj is not None

    def test_ctor_nok_wrong_topic(self):
        for topic in standard.StandardCategoryType:
            # Given
            req = _create_request(topic=topic.value + "_NOT")
            # When/Then
            with pytest.raises(ValueError):
                standard.StandardScalingCommandParser(req)

    def test_ctor_nok_wrong_resource(self):
        # Given
        req = _create_request(resource=_TEST_CLOUD_FUNCTION_RESOURCE_STR)
        # When/Then
        with pytest.raises(ValueError):
            standard.StandardScalingCommandParser(req)
