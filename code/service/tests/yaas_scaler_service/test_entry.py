# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,protected-access,duplicate-code
# type: ignore
from typing import Any, Dict, List, Optional, Union

import flask
import pytest
from yaas_common import request
from yaas_scaler import base

from tests import common
from yaas_scaler_service import entry

_TEST_REQUEST: request.ScaleRequest = common.create_scale_request()
_TEST_TOPIC_TO_PUBSUB: Dict[str, str] = {_TEST_REQUEST.topic: "test_pubsub_topic"}
_TEST_START_TS_UTC: int = 100
_TEST_END_TS_UTC: int = _TEST_START_TS_UTC + 1000


def _mock_entry(
    monkeypatch,
    *,
    event_requests: Optional[List[request.ScaleRequest]] = None,
) -> Dict[str, Any]:
    called = {}

    async def mocked_dispatch(  # pylint: disable=unused-argument
        topic_to_pubsub: Dict[str, str],
        *value: request.ScaleRequest,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> None:
        nonlocal called
        called[entry.pubsub_dispatcher.dispatch.__name__] = locals()

    def mocked_from_event(  # pylint: disable=unused-argument
        *,
        event: Union[flask.Request, Dict[str, Any]],
        iso_str_timestamp: Optional[str] = None,
    ) -> List[request.ScaleRequest]:
        nonlocal called, event_requests
        if event_requests is None:
            event_requests = [common.create_scale_request(topic=common.MyCategoryType.CATEGORY_A.name)]
        called[entry.pubsub_dispatcher.from_event.__name__] = locals()
        return event_requests

    monkeypatch.setattr(
        entry.pubsub_dispatcher,
        entry.pubsub_dispatcher.dispatch.__name__,
        mocked_dispatch,
    )
    monkeypatch.setattr(
        entry.pubsub_dispatcher,
        entry.pubsub_dispatcher.from_event.__name__,
        mocked_from_event,
    )
    return called


@pytest.mark.asyncio
async def test_enact_requests_ok(monkeypatch):
    # Given
    parser = common.MyCategoryScaleRequestParser()
    pubsub_event = common.create_event(dict(key_a="value", key_b=123, key_c=dict(key_d=321)), True)
    iso_str_timestamp = None
    kwargs = dict(
        parser=parser,
        pubsub_event=pubsub_event,
        iso_str_timestamp=iso_str_timestamp,
    )
    called = _mock_entry(monkeypatch)
    # When
    await entry.enact_requests(**kwargs)
    # Then: from event
    called_from_event = called.get(entry.pubsub_dispatcher.from_event.__name__)
    assert isinstance(called_from_event, dict)
    assert called_from_event.get("event") == kwargs.get("pubsub_event")
    assert called_from_event.get("iso_str_timestamp") == kwargs.get("iso_str_timestamp")
    # Then: parser
    scaler_args = parser.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
    assert isinstance(scaler_args, dict)
    assert scaler_args.get("result").called.get(base.Scaler._safe_enact.__name__)
