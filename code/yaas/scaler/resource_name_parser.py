# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Parses Google Cloud supported resource types.
Common resource list at `Full resource names`_.

.. _Full resource names:https://cloud.google.com/iam/docs/full-resource-names
"""
import enum
import re
from typing import Optional, Tuple

from yaas import logger

_LOGGER = logger.get(__name__)


class ResourceType(enum.Enum):
    """
    Supported Google Cloud resource type.
    """

    CLOUD_RUN = enum.auto()


def canonical_resource_type_and_name(resource: str) -> Tuple[ResourceType, str]:
    """
    Will parse the resource name, returning its type, as py:cls:`ResourceType`,
        and canonical name.

    Args:
        resource:

    Returns:
        Canonical resource name.
    """
    res_type, res_canonical = None, None
    _LOGGER.debug("Finding resource and type for <%s>", resource)
    if isinstance(resource, str):
        # Cloud Run
        cloud_run_resource = _parse_cloud_run_name(resource)
        if cloud_run_resource:
            res_type = ResourceType.CLOUD_RUN
            res_canonical = cloud_run_resource
    _LOGGER.info(
        "Parsed resource <%s> to type <%s> and canonical name <%s>",
        resource,
        res_type,
        res_canonical,
    )
    # Nothing found
    return res_type, res_canonical


######################
# Cloud Run Resource #
######################

_FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^projects/([^/\s]+)/locations/([^/\s]+)/services/([^/\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    projects/my_project/locations/europe-west3/services/my_service
Groups on matching are::
    project, location, service = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
# pylint: disable=anomalous-backslash-in-string
_SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^CloudRun\.?\s*\.?\s*"
    + r"\s+"  # separator <space>
    + r"([^@\s]+)"  # service
    + r"\s*\.?\s*@\.?\s*"  # separator @
    + r"([^\s]+)"  # project
    + r"\s*\.?\s+\.?\s*"  # separator <space>
    + r"([^\s]+)$",  # region
    flags=re.IGNORECASE,
)
# pylint: enable=anomalous-backslash-in-string
"""
Input example::
    CloudRun my_service @ my_project europe-west3
Groups on matching are::
    service, project, location = _SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
_CLOUD_RUN_RESOURCE_NAME_TMPL: str = "projects/{}/locations/{}/services/{}"


def _parse_cloud_run_name(value: str) -> Optional[str]:
    result = None
    project, location, service = None, None, None
    # FQN match
    match = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(value)
    if match:
        project, location, service = match.groups()
    else:
        match = _SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(value)
        if match:
            service, project, location = match.groups()
        else:
            _LOGGER.debug(
                "Value does not specify a CloudRun resource name. Ignoring value <%s>",
                value,
            )
    # build result
    # Why the construct below?
    # pylint: disable=line-too-long
    # https://stackoverflow.com/questions/42360956/what-is-the-most-pythonic-way-to-check-if-multiple-variables-are-not-none
    # pylint: enable=line-too-long
    if not [x for x in (project, location, service) if x is None]:
        result = _CLOUD_RUN_RESOURCE_NAME_TMPL.format(project, location, service)
    return result
