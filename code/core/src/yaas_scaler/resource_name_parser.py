# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Parses Google Cloud supported resource types. Common resource list at `Full
resource names`_.

.. _Full resource names:https://cloud.google.com/iam/docs/full-resource-names
"""
from typing import Tuple

from yaas_common import logger
from yaas_gcp import resource_regex

_LOGGER = logger.get(__name__)


def canonical_resource_type_and_name(  # pylint: disable=invalid-name
    resource: str,
) -> Tuple[resource_regex.ResourceType, str]:
    """Will parse the resource name, returning its type, as
    py:cls:`ResourceType`, and canonical name.

    Args:
        resource:

    Returns:
        Canonical resource name.
    """
    res_type, res_canonical = None, None
    _LOGGER.debug("Finding resource and type for <%s>", resource)
    if isinstance(resource, str):
        res_type, res_canonical = _canonical_resource_type_and_name(resource)
    _LOGGER.debug(
        "Parsed resource <%s> to type <%s> and canonical name <%s>",
        resource,
        res_type,
        res_canonical,
    )
    return res_type, res_canonical


def _canonical_resource_type_and_name(  # pylint: disable=invalid-name
    value: str,
) -> Tuple[resource_regex.ResourceType, str]:
    # Cloud Run
    cloud_run_resource = resource_regex.CLOUD_RUN_PARSER.canonical(value)
    if cloud_run_resource:
        return resource_regex.ResourceType.CLOUD_RUN, cloud_run_resource
    # Cloud SQL
    cloud_sql_resource = resource_regex.CLOUD_SQL_PARSER.canonical(value)
    if cloud_sql_resource:
        return resource_regex.ResourceType.CLOUD_SQL, cloud_sql_resource
    # Nothing else
    return None, None
