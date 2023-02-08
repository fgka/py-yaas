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
    CLOUD_SQL = enum.auto()


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
        res_type, res_canonical = _canonical_resource_type_and_name(resource)
    _LOGGER.info(
        "Parsed resource <%s> to type <%s> and canonical name <%s>",
        resource,
        res_type,
        res_canonical,
    )
    return res_type, res_canonical


def _canonical_resource_type_and_name(resource: str) -> Tuple[ResourceType, str]:
    # Cloud Run
    cloud_run_resource = _parse_cloud_run_name(resource)
    if cloud_run_resource:
        return ResourceType.CLOUD_RUN, cloud_run_resource
    # Cloud SQL
    cloud_sql_resource = _parse_cloud_sql_name(resource)
    if cloud_sql_resource:
        return ResourceType.CLOUD_SQL, cloud_sql_resource
    # Nothing else
    return None, None


def _parse_resource_name_by_regex(
    value: str, fqn_regex: re.Pattern, simple_regex: re.Pattern, canonical_tmpl: str
) -> Tuple[str, str, str]:
    """
    The regular expressions *MUST* return values as follows:
        * ``fqn_regex``: ``project, location, name = fqn_regex.match(value).groups()``
        * ``simple_regex``: ``name, location, project = fqn_regex.match(value).groups()``

    The template will be used as: ``canonical_tmpl.format(project, location, name)``
    Args:
        value:
        fqn_regex:
        simple_regex:
        canonical_tmpl:

    Returns:
        Canonical resource string
    """
    result = None
    project, location, name = None, None, None
    # FQN match
    match = fqn_regex.match(value)
    if match:
        project, location, name = match.groups()
    else:
        match = simple_regex.match(value)
        if match:
            name, project, location = match.groups()
        else:
            _LOGGER.debug(
                "Value does not specify a Cloud Run resource name. Ignoring value <%s>",
                value,
            )
    # build result
    # Why the construct below?
    # pylint: disable=line-too-long
    # https://stackoverflow.com/questions/42360956/what-is-the-most-pythonic-way-to-check-if-multiple-variables-are-not-none
    # pylint: enable=line-too-long
    if not [x for x in (project, location, name) if x is None]:
        result = canonical_tmpl.format(project, location, name)
    return result


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
    return _parse_resource_name_by_regex(
        value,
        _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX,
        _SIMPLE_CLOUD_RUN_TARGET_RESOURCE_REGEX,
        _CLOUD_RUN_RESOURCE_NAME_TMPL,
    )


######################
# Cloud SQL Resource #
######################

_FQN_CLOUD_SQL_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^([^/\s]+):([^/\s]+):([^/\s]+)$",
    flags=re.IGNORECASE,
)
"""
Input example::
    my_project:europe-west3:my_instance
Groups on matching are::
    project, location, instance = _FQN_CLOUD_RUN_TARGET_RESOURCE_REGEX.match(line).groups()
"""
# pylint: disable=anomalous-backslash-in-string
_SIMPLE_CLOUD_SQL_TARGET_RESOURCE_REGEX: re.Pattern = re.compile(
    pattern=r"^CloudSQL\.?\s*\.?\s*"
    + r"\s+"  # separator <space>
    + r"([^@\s]+)"  # instance
    + r"\s*\.?\s*@\.?\s*"  # separator @
    + r"([^\s]+)"  # project
    + r"\s*\.?\s+\.?\s*"  # separator <space>
    + r"([^\s]+)$",  # region
    flags=re.IGNORECASE,
)
# pylint: enable=anomalous-backslash-in-string
"""
Input example::
    CloudSql my_instance @ my_project europe-west3
Groups on matching are::
    instance, project, location = _SIMPLE_CLOUD_SQL_TARGET_RESOURCE_REGEX.match(line).groups()
"""
_CLOUD_SQL_RESOURCE_NAME_TMPL: str = "{}:{}:{}"


def _parse_cloud_sql_name(value: str) -> Optional[str]:
    return _parse_resource_name_by_regex(
        value,
        _FQN_CLOUD_SQL_TARGET_RESOURCE_REGEX,
        _SIMPLE_CLOUD_SQL_TARGET_RESOURCE_REGEX,
        _CLOUD_SQL_RESOURCE_NAME_TMPL,
    )
