# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Dict, Generator, Optional

import pytest

from yaas_common import const
from yaas_config import config, resolve_config
from yaas_gcp import gcs

from tests import common


def _config(topic_to_pubsub_gcs: Optional[str] = None) -> config.Config:
    return common.TEST_CONFIG_LOCAL_JSON.clone(topic_to_pubsub_gcs=topic_to_pubsub_gcs)


class _MyBlob:
    def __init__(self, name: str, content: Optional[bytes] = None):
        self.name = name
        self._content = content
        self.called = {}

    def download_as_bytes(self) -> bytes:
        self.called[_MyBlob.download_as_bytes.__name__] = True
        return self._content


@pytest.mark.parametrize(
    "value,extra_topics",
    [
        (_config(None), {}),
        (
            _config("gs://test-bucket/path/to/prefix"),
            {
                "extra-topic-1": "projects/test-project/topics/test-topic-1",
                "extra-topic-2": "projects/test-project/topics/test-topic-2",
            },
        ),
    ],
)
def test_consolidate_config_ok(
    monkeypatch, value: config.Config, extra_topics: Dict[str, str]
):
    # Given
    called = _mock_list_objects(monkeypatch, extra_topics)
    # When
    result = resolve_config.consolidate_config(value)
    # Then
    _verify_unchanged(result, value)
    # Then: extra topics
    if extra_topics:
        _verify_list_called(
            called.get(resolve_config.gcs.list_objects.__name__), result
        )
        for topic, topic_id in extra_topics.items():
            assert result.topic_to_pubsub.get(topic) == topic_id
    else:
        assert not called


def _mock_list_objects(
    monkeypatch, extra_topics: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    called = {}

    def mocked_list_objects(  # pylint: disable=unused-argument
        *,
        bucket_name: str,
        prefix: str,
        project: Optional[str] = None,
    ) -> Generator[_MyBlob, None, None]:
        nonlocal called, extra_topics
        called[resolve_config.gcs.list_objects.__name__] = locals()
        for topic, topic_id in extra_topics.items():
            yield _MyBlob(
                name=topic,
                content=bytes(
                    topic_id.encode(const.ENCODING_UTF8)
                    if isinstance(topic_id, str)
                    else topic_id
                ),
            )

    monkeypatch.setattr(
        resolve_config.gcs,
        resolve_config.gcs.list_objects.__name__,
        mocked_list_objects,
    )
    return called


def _verify_list_called(called, result):
    bucket_name, prefix = gcs.get_bucket_and_prefix_from_uri(result.topic_to_pubsub_gcs)
    assert isinstance(called, dict)
    assert called.get("bucket_name") == bucket_name
    assert called.get("prefix") == prefix


def _verify_unchanged(result, value):
    assert isinstance(result, config.Config)
    assert result.calendar_config == value.calendar_config
    assert result.cache_config == value.cache_config
    assert result.topic_to_pubsub_gcs == value.topic_to_pubsub_gcs
    assert result.retention_config == value.retention_config
    # Then: topic_to_pubsub
    for topic, topic_id in value.topic_to_pubsub.items():
        assert result.topic_to_pubsub.get(topic) == topic_id


def test_consolidate_config_nok(monkeypatch):
    # Given
    value = _config("gs://test-bucket/path/to/prefix")
    extra_topics = {
        "extra-topic-1": "projects/test-project/topics",
        "extra-topic-2": bytes(123),
    }
    for topic, topic_id in value.topic_to_pubsub.items():
        extra_topics[topic] = f"{topic_id}-not"
    called = _mock_list_objects(monkeypatch, extra_topics)
    # When
    result = resolve_config.consolidate_config(value)
    # Then
    _verify_unchanged(result, value)
    _verify_list_called(called.get(resolve_config.gcs.list_objects.__name__), result)
    # Then: topic_to_pubsub
    for topic, topic_id in extra_topics.items():
        if topic in value.topic_to_pubsub:
            assert result.topic_to_pubsub.get(topic) != topic_id
        else:
            assert topic not in result.topic_to_pubsub
