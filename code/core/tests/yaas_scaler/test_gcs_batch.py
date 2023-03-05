# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,protected-access
# pylint: disable=invalid-name,attribute-defined-outside-init,duplicate-code
# type: ignore
import pathlib
from typing import Any, Dict, List, Optional

import pytest

from tests import common
from yaas_calendar import parser
from yaas_common import const, request
from yaas_scaler import gcs_batch


class TestGcsBatchScalingCommand:
    @pytest.mark.parametrize("parameter", ["object.ext", "path/to/object.ext", "object", "path/to/object"])
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
    return gcs_batch.GcsBatchScalingDefinition(resource=resource, command=command, timestamp_utc=timestamp_utc)


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
        command = gcs_batch.GcsBatchScalingCommand(parameter=_TEST_GCS_BATCH_COMMAND_STR)
        # When/Then
        with pytest.raises(ValueError):
            gcs_batch.GcsBatchScalingDefinition(resource=resource, command=command, timestamp_utc=321)

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
    "gcs_batch": "test-pubsub-topic-gcs",
    "yaas": "test-pubsub-topic-yaas",
    "standard": "test-pubsub-topic-standard",
}
_TEST_TOPIC_DEFINITION: Dict[str, List[gcs_batch.GcsBatchScalingDefinition]] = {
    topic: [
        _create_gcs_batch_scaling_definition(parameter=f"{_TEST_GCS_BATCH_COMMAND_STR}.{topic}.{ndx}")
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
            _create_gcs_batch_scaling_definition(parameter=f"{_TEST_GCS_BATCH_COMMAND_STR}.{ndx}") for ndx in range(11)
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
    async def test__process_definition(self, monkeypatch):
        # Given
        definition = _TEST_DEFINITIONS[-1]
        gcs_content = _TEST_GCS_CONTENT
        called = self._mock_gcs_batch(monkeypatch, gcs_content=gcs_content)
        # When
        await self.obj._process_definition(definition)
        # Then: gcs
        gcs_called = called.get(gcs_batch.gcs.read_object.__name__)
        assert isinstance(gcs_called, list)
        assert len(gcs_called) == 1
        assert gcs_called[0].get("bucket_name") == definition.resource
        assert gcs_called[0].get("object_path") == definition.command.parameter
        # Then: pubsub
        pubsub_called = called.get(gcs_batch.pubsub_dispatcher.dispatch.__name__)
        assert isinstance(pubsub_called, list)
        assert len(pubsub_called) == 1
        assert pubsub_called[0].get("topic_to_pubsub") == self.obj.topic_to_pubsub
        # Then: pubsub request
        pubsub_req_lst = pubsub_called[0].get("value")
        assert len(pubsub_req_lst) == 1
        pubsub_req = pubsub_req_lst[0]
        assert isinstance(pubsub_req, request.ScaleRequest)
        expected_req = parser.parse_lines(
            lines=[
                str(
                    gcs_content.get(definition.command.parameter),
                    encoding=const.ENCODING_UTF8,
                )
            ],
            timestamp_utc=definition.timestamp_utc,
            json_event=definition.as_json(),
        )
        assert pubsub_req == expected_req[0]

    @staticmethod
    def _mock_gcs_batch(monkeypatch, gcs_content: Dict[str, Any] = _TEST_GCS_CONTENT):
        called = {}

        def mocked_read_object(  # pylint: disable=unused-argument
            *,
            bucket_name: str,
            object_path: str,
            project: Optional[str] = None,
            filename: Optional[pathlib.Path] = None,
            warn_read_failure: Optional[bool] = True,
        ) -> Optional[bytes]:
            var_locals = locals()
            nonlocal called, gcs_content
            key = gcs_batch.gcs.read_object.__name__
            if key not in called:
                called[key] = []
            called[key].append(var_locals)
            return gcs_content.get(object_path)

        async def mocked_dispatch(  # pylint: disable=unused-argument
            topic_to_pubsub: Dict[str, str],
            *value: request.ScaleRequest,
            raise_if_invalid_request: Optional[bool] = True,
        ) -> None:
            var_locals = locals()
            nonlocal called
            key = gcs_batch.pubsub_dispatcher.dispatch.__name__
            if key not in called:
                called[key] = []
            called[key].append(var_locals)

        monkeypatch.setattr(gcs_batch.gcs, gcs_batch.gcs.read_object.__name__, mocked_read_object)
        monkeypatch.setattr(
            gcs_batch.pubsub_dispatcher,
            gcs_batch.pubsub_dispatcher.dispatch.__name__,
            mocked_dispatch,
        )
        return called

    def test__filter_requests_ok(self):
        # Given
        value = [
            parser.parse_lines(lines=[str(val, encoding=const.ENCODING_UTF8)], timestamp_utc=123)[0]
            for val in _TEST_GCS_CONTENT.values()
        ]
        wrong_values = [val for val in value if gcs_batch.GcsBatchCategoryType.from_str(val.topic) is not None]
        # When
        result = gcs_batch.GcsBatchScaler._filter_requests(value)
        # Then
        assert isinstance(result, list)
        assert result
        assert value
        assert wrong_values
        assert len(result) == len(value) - len(wrong_values)
        # Then: items in result
        for item in result:
            assert item not in wrong_values
            assert gcs_batch.GcsBatchCategoryType.from_str(item.topic) is None

    @pytest.mark.asyncio
    async def test__safe_enact_ok(self, monkeypatch):
        # Given
        topic_to_pubsub = _TEST_TOPIC_TO_PUBSUB
        obj = gcs_batch.GcsBatchScaler(*_TEST_DEFINITIONS, topic_to_pubsub=topic_to_pubsub)
        called = []

        async def mocked_process_definition(
            definition: gcs_batch.GcsBatchScalingDefinition,
        ) -> None:
            nonlocal called
            called.append(definition)

        monkeypatch.setattr(obj, obj._process_definition.__name__, mocked_process_definition)
        # When
        await obj._safe_enact()
        # Then
        assert len(called) == len(_TEST_DEFINITIONS)
        assert len(called) == len(set(called))
        for scale_def in called:
            assert scale_def in _TEST_DEFINITIONS


def _create_request(
    *,
    topic: str = gcs_batch.GcsBatchCategoryType.default().value,
    resource: str = _TEST_GCS_BATCH_RESOURCE_STR,
    command: str = _TEST_GCS_BATCH_COMMAND_STR,
) -> request.ScaleRequest:
    return common.create_scale_request(
        topic=topic,
        resource=resource,
        command=command,
    )


class TestStandardScalingCommandParser:
    def setup(self):
        self.obj = gcs_batch.GcsBatchCommandParser(topic_to_pubsub=_TEST_TOPIC_TO_PUBSUB)

    def test_scaler_ok(self):
        for topic in gcs_batch.GcsBatchCategoryType:
            # Given
            req = _create_request(
                topic=topic.value,
                resource=_TEST_GCS_BATCH_RESOURCE_STR,
                command=_TEST_GCS_BATCH_COMMAND_STR,
            )
            # When
            result = self.obj.scaler(req)
            # Then
            assert isinstance(result, gcs_batch.GcsBatchScaler)

    def test_scaler_nok_wrong_topic(self):
        for topic in gcs_batch.GcsBatchCategoryType:
            # Given
            req = _create_request(topic=topic.value + "_NOT")
            # When/Then
            with pytest.raises(ValueError):
                self.obj.scaler(req)

    def test_scaler_nok_wrong_resource(self):
        # Given
        req = _create_request(resource=_TEST_GCS_BATCH_RESOURCE_STR + "/")
        # When/Then
        with pytest.raises(ValueError):
            self.obj.scaler(req)

    @pytest.mark.parametrize(
        "value",
        [
            request.ScaleRequest(
                topic="gcs",
                resource="my-test-bucket-a",
                command="path/to/object_a",
                timestamp_utc=123,
                original_json_event=None,
            ),
            request.ScaleRequest(
                topic="gcs_batch",
                resource="my-test-bucket-b",
                command="path/to/object_b",
                timestamp_utc=123,
                original_json_event=None,
            ),
        ],
    )
    def test__scaling_definition_from_request_ok(self, value: request.ScaleRequest):
        # Given/When
        result = self.obj._scaling_definition_from_request(value)
        # Then
        assert isinstance(result, gcs_batch.GcsBatchScalingDefinition)
        assert result.resource == value.resource
        assert result.command.parameter == value.command
