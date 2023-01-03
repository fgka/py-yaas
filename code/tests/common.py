# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import tempfile
from typing import Any, Dict

from yaas.dto import config, event, request
from yaas.scaler import standard

_TEST_SCALE_REQUEST_KWARGS: Dict[str, Any] = dict(
    topic="TEST_TOPIC",
    resource="TEST_RESOURCE",
    command="TEST_COMMAND",
    timestamp_utc=123,
    original_json_event="TEST_ORIGINAL_JSON_EVENT",
)


def create_scale_request(**kwargs) -> request.ScaleRequest:
    scale_kwargs = {
        **_TEST_SCALE_REQUEST_KWARGS,
        **kwargs,
    }
    return request.ScaleRequest(**scale_kwargs)


TEST_CALENDAR_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="calendar")
TEST_CACHE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="cache")
TEST_COMPARISON_SNAPSHOT: event.EventSnapshotComparison = event.EventSnapshotComparison(
    snapshot_a=TEST_CALENDAR_SNAPSHOT,
    snapshot_b=TEST_CACHE_SNAPSHOT,
)
TEST_MERGE_SNAPSHOT: event.EventSnapshot = event.EventSnapshot(source="merge")


_TEST_PUBSUB_TOPIC: str = "test_yaas_pubsub_topic"

# pylint: disable=consider-using-with
TEST_CONFIG_LOCAL_JSON: config.Config = config.Config(
    calendar_config=config.CalendarCacheConfig(
        type=config.CacheType.CALENDAR.value,
        calendar_id="test_calendar_id",
        secret_name="test_calendar_secret_name",
    ),
    cache_config=config.LocalJsonLineCacheConfig(
        type=config.CacheType.LOCAL_JSON_LINE.value,
        json_line_file=tempfile.NamedTemporaryFile().name,
        archive_json_line_file=tempfile.NamedTemporaryFile().name,
    ),
    topic_to_pubsub={
        standard.StandardCategoryType.YAAS.value: _TEST_PUBSUB_TOPIC,
        standard.StandardCategoryType.STANDARD.value: _TEST_PUBSUB_TOPIC,
    },
)
# pylint: enable=consider-using-with
