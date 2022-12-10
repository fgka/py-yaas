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
