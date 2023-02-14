# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# pylint: disable=duplicate-code
# type: ignore
from typing import Any, Dict, List, Optional, Tuple
import pytest

from yaas.scaler import gcs_batch

from tests import common


class TestGcsBatchScalingCommand:
    @pytest.mark.parametrize(
        "parameter", ["object.ext", "path/to/object.ext", "object", "path/to/object"]
    )
    def test_ctor_ok(self, parameter: str):
        # Given/When
        obj = gcs_batch.GcsBatchScalingCommand(parameter=parameter)
        # Then
        assert isinstance(obj, gcs_batch.GcsBatchScalingCommand)
        assert obj.parameter == parameter
        assert obj.target is None

    @pytest.mark.parametrize(
        "parameter",
        [
            None,
            123,
            "",
            "/",
            "prefix/",
            "/prefix/",
            "/prefix/.",
        ],
    )
    def test_ctor_nok(self, parameter: str):
        with pytest.raises(TypeError):
            gcs_batch.GcsBatchScalingCommand(parameter=parameter)

    def test_from_command_str_ok(self):
        # Given
        parameter = "yaas/path/to/object.ext"
        # When
        obj = gcs_batch.GcsBatchScalingCommand(parameter=parameter)
        # Then
        assert isinstance(obj, gcs_batch.GcsBatchScalingCommand)
        assert obj.parameter == parameter
        assert obj.target is None


_TEST_GCS_BATCH_RESOURCE_STR: str = "test-bucket-name"
_TEST_GCS_BATCH_COMMAND_STR: str = "path/to/object.ext"


def _create_gcs_batch_scaling_definition(
    *,
    resource: str = _TEST_GCS_BATCH_RESOURCE_STR,
    parameter: str = _TEST_GCS_BATCH_COMMAND_STR,
    timestamp_utc: int = 321,
) -> gcs_batch.GcsBatchScalingDefinition:
    command = gcs_batch.GcsBatchScalingCommand(parameter=parameter)
    return gcs_batch.GcsBatchScalingDefinition(
        resource=resource, command=command, timestamp_utc=timestamp_utc
    )


class TestGcsBatchScalingDefinition:
    def test_ctor_ok(self):
        # Given
        resource = _TEST_GCS_BATCH_RESOURCE_STR
        # When
        obj = _create_gcs_batch_scaling_definition(resource=resource)
        # Then
        assert isinstance(obj, gcs_batch.GcsBatchScalingDefinition)
        assert obj.resource == resource

    def test_ctor_nok_wrong_resource(self):
        # Given
        resource = "NOT/" + _TEST_GCS_BATCH_RESOURCE_STR
        command = gcs_batch.GcsBatchScalingCommand(
            parameter=_TEST_GCS_BATCH_COMMAND_STR
        )
        # When/Then
        with pytest.raises(ValueError):
            gcs_batch.GcsBatchScalingDefinition(
                resource=resource, command=command, timestamp_utc=321
            )

    def test_from_request_ok(self):
        # Given
        req = common.create_scale_request(
            resource=_TEST_GCS_BATCH_RESOURCE_STR,
            command=_TEST_GCS_BATCH_COMMAND_STR,
        )
        # When
        obj = gcs_batch.GcsBatchScalingDefinition.from_request(req)
        # Then
        assert isinstance(obj, gcs_batch.GcsBatchScalingDefinition)
        assert obj.resource == req.resource


_TEST_TOPIC_TO_PUBSUB: Dict[str, str] = {
    "gcs": "test-pubsub-topic-gcs",
    "yaas": "test-pubsub-topic-yaas",
    "standard": "test-pubsub-topic-standard",
}


class TestGcsBatchScaler:
    def setup(self):
        self.definition = [
            _create_gcs_batch_scaling_definition(
                parameter=f"{_TEST_GCS_BATCH_COMMAND_STR}.{ndx}"
            )
            for ndx in range(11)
        ]
        self.obj = gcs_batch.GcsBatchScaler(*self.definition, topic_to_pubsub=_TEST_TOPIC_TO_PUBSUB)

    def test_ctor_ok(self):
        # Given
        topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
        # When
        obj = gcs_batch.GcsBatchScaler(*self.definition, topic_to_pubsub=topic_to_pubsub)
        # Then
        assert isinstance(obj, gcs_batch.GcsBatchScaler)
        assert obj.topic_to_pubsub == topic_to_pubsub

    def test_from_request_ok(self):
        # Given
        topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
        req = common.create_scale_request(
            resource=_TEST_GCS_BATCH_RESOURCE_STR,
            command=_TEST_GCS_BATCH_COMMAND_STR,
        )
        # When
        obj = gcs_batch.GcsBatchScaler.from_request(req, topic_to_pubsub=topic_to_pubsub)
        # Then
        assert isinstance(obj, gcs_batch.GcsBatchScaler)
        assert obj.resource == req.resource

    @pytest.mark.asyncio
    async def test_can_enact_ok(self):
        # Given/When
        res, reason = await self.obj.can_enact()
        # Then
        assert res
        assert isinstance(reason, str)
        assert not reason

    @pytest.mark.asyncio
    async def test__safe_enact_ok(self):
        # Given
        topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
        req = common.create_scale_request(
            resource=_TEST_GCS_BATCH_RESOURCE_STR,
            command=_TEST_GCS_BATCH_COMMAND_STR,
        )
        obj = gcs_batch.GcsBatchScaler.from_request(req, topic_to_pubsub=topic_to_pubsub)
        # When
        await obj._safe_enact()
        # Then