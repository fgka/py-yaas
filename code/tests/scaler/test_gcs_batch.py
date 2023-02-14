# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# pylint: disable=duplicate-code
# type: ignore
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import pytest

from yaas import const
from yaas.dto import request
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
_TEST_TOPIC_DEFINITION: Dict[str, List[gcs_batch.GcsBatchScalingDefinition]] = {
    topic: [
        _create_gcs_batch_scaling_definition(
            parameter=f"{_TEST_GCS_BATCH_COMMAND_STR}.{topic}.{ndx}"
        )
        for ndx in range(3)
    ]
    for topic in _TEST_TOPIC_TO_PUBSUB
}
_TEST_DEFINITIONS: List[gcs_batch.GcsBatchScalingDefinition] = [
    item for sublist in _TEST_TOPIC_DEFINITION.values() for item in sublist
]
_TEST_GCS_CONTENT: Dict[str, Any] = {
    definition.command.parameter: f"{topic} | some_resource.{topic} | some_cmd.{definition.command.parameter}".encode(
        const.ENCODING_UTF8
    )
    for topic, def_lst in _TEST_TOPIC_DEFINITION.items()
    for definition in def_lst
}


class TestGcsBatchScaler:
    def setup(self):
        self.definition = [
            _create_gcs_batch_scaling_definition(
                parameter=f"{_TEST_GCS_BATCH_COMMAND_STR}.{ndx}"
            )
            for ndx in range(11)
        ]
        self.obj = gcs_batch.GcsBatchScaler(
            *self.definition, topic_to_pubsub=_TEST_TOPIC_TO_PUBSUB
        )

    def test_ctor_ok(self):
        # Given
        topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
        # When
        obj = gcs_batch.GcsBatchScaler(
            *self.definition, topic_to_pubsub=topic_to_pubsub
        )
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
        obj = gcs_batch.GcsBatchScaler.from_request(
            req, topic_to_pubsub=topic_to_pubsub
        )
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
    async def test__process_definition(self, monkeypatch):
        # Given
        definition = _TEST_DEFINITIONS[0]
        called = self._mock_gcs_batch(monkeypatch)
        # When
        await self.obj._process_definition(definition)
        # Then: gcs
        gcs_called = called.get(gcs_batch.gcs.read_object.__name__)
        assert isinstance(gcs_called, list)
        # Then: pubsub
        pubsub_called = called.get(gcs_batch.pubsub_dispatcher.dispatch.__name__)
        assert isinstance(pubsub_called, list)

    @staticmethod
    def _mock_gcs_batch(monkeypatch, gcs_content: Dict[str, Any] = _TEST_GCS_CONTENT):
        called = {}

        def mocked_read_object(
            *,
            bucket_name: str,
            object_path: str,
            project: Optional[str] = None,
            filename: Optional[pathlib.Path] = None,
            warn_read_failure: Optional[bool] = True,
        ) -> Optional[bytes]:
            vars = locals()
            nonlocal called, gcs_content
            key = gcs_batch.gcs.read_object.__name__
            if key not in called:
                called[key] = []
            called[key].append(vars)
            return gcs_content.get(object_path)

        async def mocked_dispatch(
            topic_to_pubsub: Dict[str, str],
            *value: request.ScaleRequest,
            raise_if_invalid_request: Optional[bool] = True,
        ) -> None:
            vars = locals()
            nonlocal called
            key = gcs_batch.pubsub_dispatcher.dispatch.__name__
            if key not in called:
                called[key] = []
            called[key].append(vars)

        monkeypatch.setattr(
            gcs_batch.gcs, gcs_batch.gcs.read_object.__name__, mocked_read_object
        )
        monkeypatch.setattr(
            gcs_batch.pubsub_dispatcher,
            gcs_batch.pubsub_dispatcher.dispatch.__name__,
            mocked_dispatch,
        )
        return called

    @pytest.mark.asyncio
    async def test__safe_enact_ok(self):
        # Given
        topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
        req = common.create_scale_request(
            resource=_TEST_GCS_BATCH_RESOURCE_STR,
            command=_TEST_GCS_BATCH_COMMAND_STR,
        )
        obj = gcs_batch.GcsBatchScaler.from_request(
            req, topic_to_pubsub=topic_to_pubsub
        )
        # When
        await obj._safe_enact()
        # Then
