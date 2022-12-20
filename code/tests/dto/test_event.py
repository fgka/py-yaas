# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Dict, List

import pytest

from yaas.dto import event, request


_TEST_SCALE_REQUEST: request.ScaleRequest = request.ScaleRequest(
    topic="TEST_TOPIC", resource="TEST_RESOURCE"
)


class TestEventSnapshot:
    def test_range_ok_no_timestamp_to_request(self):
        # Given
        obj = event.EventSnapshot(source="TEST_SNAPSHOT")
        # When
        result = obj.range()
        # Then
        assert result is None

    def test_range_ok_empty_timestamp_to_request(self):
        # Given
        obj = event.EventSnapshot(source="TEST_SNAPSHOT", timestamp_to_request={})
        # When
        result = obj.range()
        # Then
        assert result is None

    @pytest.mark.parametrize(
        "timestamp_to_request,min_ts,max_ts",
        [
            ({0: [_TEST_SCALE_REQUEST]}, 0, 0),
            ({0: [_TEST_SCALE_REQUEST], 123: [_TEST_SCALE_REQUEST]}, 0, 123),
            (
                {
                    0: [_TEST_SCALE_REQUEST],
                    51: [_TEST_SCALE_REQUEST],
                    123: [_TEST_SCALE_REQUEST],
                },
                0,
                123,
            ),
            (
                {
                    123: [_TEST_SCALE_REQUEST],
                    0: [_TEST_SCALE_REQUEST],
                    51: [_TEST_SCALE_REQUEST],
                },
                0,
                123,
            ),
        ],
    )
    def test_range_ok(
        self,
        timestamp_to_request: Dict[int, List[request.ScaleRequest]],
        min_ts: int,
        max_ts: int,
    ):
        # Given
        obj = event.EventSnapshot(
            source="TEST_SNAPSHOT", timestamp_to_request=timestamp_to_request
        )
        # When
        res_min_ts, res_max_ts = obj.range()
        # Then
        assert res_min_ts == min_ts
        assert res_max_ts == max_ts

    @pytest.mark.parametrize(
        "request_lst",
        [
            ([]),
            (
                [
                    request.ScaleRequest(
                        topic="TEST_TOPIC", resource="TEST_RESOURCE", timestamp_utc=123
                    )
                ]
            ),
            (
                [
                    request.ScaleRequest(
                        topic="TEST_TOPIC",
                        resource="TEST_RESOURCE_A",
                        timestamp_utc=123,
                    ),
                    request.ScaleRequest(
                        topic="TEST_TOPIC",
                        resource="TEST_RESOURCE_B",
                        timestamp_utc=123,
                    ),
                ]
            ),
            (
                [
                    request.ScaleRequest(
                        topic="TEST_TOPIC",
                        resource="TEST_RESOURCE_A",
                        timestamp_utc=123,
                    ),
                    request.ScaleRequest(
                        topic="TEST_TOPIC",
                        resource="TEST_RESOURCE_B",
                        timestamp_utc=321,
                    ),
                ]
            ),
        ],
    )
    def test_from_list_requests_ok(self, request_lst):
        source = "TEST_SOURCE"
        result = event.EventSnapshot.from_list_requests(
            source=source, request_lst=request_lst, discard_invalid=False
        )
        # Then
        assert isinstance(result, event.EventSnapshot)
        assert result.source == source
        all_request = []
        for ts, lst_req in result.timestamp_to_request.items():
            for req in lst_req:
                assert req.timestamp_utc == ts
            all_request.extend(lst_req)
        assert len(all_request) == len(request_lst)

    def test_from_list_requests_ok_discard(self):
        # Given
        req = request.ScaleRequest(
            topic="TEST_TOPIC", resource="TEST_RESOURCE", timestamp_utc=None
        )
        # When
        result = event.EventSnapshot.from_list_requests(
            source="TEST_SOURCE", request_lst=[req], discard_invalid=True
        )
        # Then
        assert isinstance(result, event.EventSnapshot)
        assert not result.timestamp_to_request

    def test_from_list_requests_nok(self):
        req = request.ScaleRequest(
            topic="TEST_TOPIC", resource="TEST_RESOURCE", timestamp_utc=None
        )
        with pytest.raises(ValueError):
            event.EventSnapshot.from_list_requests(
                source="TEST_SOURCE", request_lst=[req], discard_invalid=False
            )