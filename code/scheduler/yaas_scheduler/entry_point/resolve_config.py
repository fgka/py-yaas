# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Act on the ``topic_to_pubsub_gcs`` to resolve extra topics on :py:class:`config.Config`.
"""
from typing import Optional

from yaas.dto import config
from yaas.gcp import gcs, pubsub
from yaas import const, logger

_LOGGER = logger.get(__name__)


def consolidate_config(
    value: config.Config, *, raise_if_failed: Optional[bool] = True
) -> config.Config:
    # pylint: disable=line-too-long
    """
    This will return a clone of the argument with ``topic_to_pubsub_gcs``
    resolved into ``topic_to_pubsub``.
    What it will do:
    1. List all objects in ``topic_to_pubsub_gcs``;
    1. For each object:
        1. The object name is the topic name, e.g., ``on-prem``;
        1. The content is the Pub/Sub topic id, e.g., ``projects/my-project/topics/my-topic``;
    1. Add, without overwriting, these to ``topic_to_pubsub``.

    Example::
        # other members are omitted
        value = {
            "topic_to_pubsub": {
                "standard": "projects/my-project/topics/yaas_gcp-scaler-scheduler-common-enact-standard-request",
                "yaas_gcp-scaler-scheduler-common": "projects/my-project/topics/yaas_gcp-scaler-scheduler-common-enact-standard-request",
                "gcs": "projects/my-project/topics/yaas_gcp-scaler-scheduler-common-enact-gcs-batch-request"
            },
            "topic_to_pubsub_gcs": "gs://my-bucket/yaas_gcp-scaler-scheduler-common/topic_to_pubsub"
        }
        print("gs://my-bucket/yaas_gcp-scaler-scheduler-common/topic_to_pubsub/my-new-topic") == "projects/my-new-project/topics/yaas_gcp-scaler-scheduler-common-enact-my-new-topic"

    Then after this you will have::
        # other members are omitted
        value = {
            "topic_to_pubsub": {
                "standard": "projects/my-project/topics/yaas_gcp-scaler-scheduler-common-enact-standard-request",
                "yaas_gcp-scaler-scheduler-common": "projects/my-project/topics/yaas_gcp-scaler-scheduler-common-enact-standard-request",
                "gcs": "projects/my-project/topics/yaas_gcp-scaler-scheduler-common-enact-gcs-batch-request",
                "my-new-topic": "projects/my-new-project/topics/yaas_gcp-scaler-scheduler-common-enact-my-new-topic"
            },
            "topic_to_pubsub_gcs": "gs://my-bucket/yaas_gcp-scaler-scheduler-common/topic_to_pubsub"
        }


    Args:
        value:
        raise_if_failed:

    Returns:

    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Consolidating config for: <%s>", value)
    # input validation
    if not isinstance(value, config.Config):
        raise TypeError(
            f"Value must be an instance of {config.Config.__name__}. "
            f"Got: <{value}>({type(value)})"
        )
    # logic
    result = value
    if value.topic_to_pubsub_gcs:
        try:
            result = _consolidate_config_with_topic_to_pubsub_gcs(value)
        except Exception as err:  # pylint: disable=broad-exception-caught
            msg = (
                f"Could not consolidate Pub/Sub mapping using <{value.topic_to_pubsub_gcs}>."
                f" Error: {err}"
            )
            if raise_if_failed:
                raise RuntimeError(msg) from err
            _LOGGER.warning(msg)
    return result


def _consolidate_config_with_topic_to_pubsub_gcs(value: config.Config) -> config.Config:
    if not value.topic_to_pubsub_gcs:
        raise RuntimeError(f"Expecting to have 'topic_to_pubsub_gcs' in {value}")
    topic_to_pubsub = value.topic_to_pubsub.copy()
    bucket_name, prefix = gcs.get_bucket_and_prefix_from_uri(value.topic_to_pubsub_gcs)
    for blob in gcs.list_objects(bucket_name=bucket_name, prefix=prefix):
        topic = blob.name.split(gcs.GCS_PATH_SEP)[-1]
        blob_uri = f"gs://{bucket_name}/{blob.name}"
        # topic_to_pubsub has precedence over GCS
        if topic in topic_to_pubsub:
            _LOGGER.warning(
                "Topic <%s> is already present in topic_to_pubsub. Ignoring content in%s",
                topic,
                blob_uri,
            )
            continue
        # is new topic
        topic_id = blob.download_as_bytes().decode(encoding=const.ENCODING_UTF8)
        try:
            pubsub.validate_topic_id(topic_id)
            topic_to_pubsub[topic] = topic_id
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(
                "Content of %s is not a valid Pub/Sub topic id. Content: <%s>. Error: %s",
                blob_uri,
                topic_id,
                err,
            )
    # build object
    return value.clone(topic_to_pubsub=topic_to_pubsub)
