# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCP `Cloud SQL`_ entry point focused on control plane APIs. The client is a
generic client based on `discovery`_. The full `REST API`_ documentation
indicates how to use the generic client.

.. _Cloud SQL: https://github.com/googleapis/google-api-python-client
.. _discovery: https://googleapis.github.io/google-api-python-client/docs/start.html
.. _REST API: https://cloud.google.com/sql/docs/postgres/admin-api/rest
"""
import asyncio
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient import discovery

from yaas_common import logger, validation, xpath
from yaas_gcp import cloud_sql_const, resource_regex

_LOGGER = logger.get(__name__)


class CloudSqlServiceError(Exception):
    """To encapsulate all exceptions operating on Cloud SQL."""


async def get_instance(value: str) -> Dict[str, Any]:
    """
    Returns a :py:class:`dict` for the `DatabaseInstance`_
    Args:
        value: full instance name, e.g.::
            my-project-123:my-location-123:my-instance-123

    Returns:
        Service

    Raises:
        CloudSqlServiceError: any error accessing the Cloud SQL control plane.

    .. DatabaseInstance: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#DatabaseInstance
    """
    _LOGGER.debug("Getting instance '%s'", value)
    # validate
    project, _, instance_name = _sql_fqn_components(value)
    # get service definition
    await asyncio.sleep(0)
    try:
        request = _sql_instances().get(project=project, instance=instance_name)
        await asyncio.sleep(0)
        result = request.execute()
        await asyncio.sleep(0)
    except Exception as err:
        raise CloudSqlServiceError(f"Could not retrieve service '{value}'. Error: {err}") from err
    return result


def _sql_fqn_components(value: str) -> Tuple[str, str, str]:
    """
    Components in the following fashion::
        project, location, instance_name = _sql_fqn_components(value)

    Args:
        value:

    Returns:

    """
    parsed = resource_regex.CLOUD_SQL_CANONICAL_REGEX.prj_loc_name(value)
    if parsed:
        project, location, instance_name = parsed
    else:
        raise ValueError(
            f"Instance name '{value}' is not a valid Cloud SQL resource name. "
            f"Needs to comply with '{resource_regex.CLOUD_SQL_CANONICAL_REGEX}'"
        )
    return project, location, instance_name


async def can_be_deployed(value: str) -> Tuple[bool, str]:
    """A wrapper around :py:func:`get_instance` and returning :py:obj:`True` if
    `DatabaseInstance`_ state is `RUNNABLE`_.

    Args:
        value:

    Returns:
        A tuple in the form ``('can_enact: bool', 'reason for False: str')``.

    .. _DatabaseInstance: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#DatabaseInstance
    .. _RUNNABLE: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#SqlInstanceState
    """
    reason = None
    _LOGGER.debug("Checking readiness of instance '%s'", value)
    try:
        # service
        instance = await get_instance(value)
        status = instance.get(cloud_sql_const.CLOUD_SQL_STATE_KEY)
        # checking status
        if status != cloud_sql_const.CLOUD_SQL_STATUS_OK:
            reason = (
                f"Instance '{value}' {cloud_sql_const.CLOUD_SQL_STATE_KEY} "
                f"'{status}'({type(status)}) is not {cloud_sql_const.CLOUD_SQL_STATUS_OK}, "
                "try again later."
            )
    except Exception as err:  # pylint: disable=broad-except
        reason = f"Could not retrieve service with name '{value}'. Error: {err}"
        _LOGGER.exception(reason)
    return reason is None, reason


def validate_cloud_sql_resource_name(  # pylint: disable=invalid-name
    value: str, *, raise_if_invalid: bool = True
) -> List[str]:
    """Validates the ``value`` against the pattern:: my-project-123:my-
    location-123:my-instance-123.

    Args:
        value: Could SQL resource name to be validated.
        raise_if_invalid: if :py:obj:`True` will raise exception if ``value`` is not valid.

    Returns:
        If ``raise_if_invalid`` if :py:obj:`False` will contain all reasons
            why the validation failed.
    """
    result = []
    try:
        _sql_fqn_components(value)
    except Exception as err:  # pylint: disable=broad-except
        if raise_if_invalid:
            raise err
        result.append(f"Could not parse instance name '{value}'. Error: {err}")
    return result


def _sql_instances() -> discovery.Resource:
    # pylint: disable=no-member
    return _sql_client().instances()


def _sql_client() -> discovery.Resource:
    """Based on: https://cloud.google.com/sql/docs/postgres/admin-
    api/libraries.

    *NOTE*: all engines are the same way.
    """
    return discovery.build("sqladmin", "v1beta4")


async def update_instance(*, name: str, path_value_lst: List[Tuple[str, Optional[Any]]]) -> Dict[str, Any]:
    """Wrapper for :py:meth:`instances.patch` (`documentation`_). The
    `path_value_lst` is a list of :py:class:`tuple` and has the following
    format: ``[(<path>,<value>,)]`` where:

        - ``path`` follows a simple `x-path`_ like path to the value
            to be updated in the Cloud SQL instance.
        - ``value`` the, optional, value that the attribute should assume.

    Args:
        name: full service name, e.g.:
            `my-project-123:my-location-123:my-instance-123`.
        path_value_lst: list of tuples ``[(<path>,<value>,)]``

    Returns:

    .. _documentation: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances/patch
    .. _x-path: https://en.wikipedia.org/wiki/XPath
    """
    _LOGGER.debug("Updating instance '%s' with '%s'", name, path_value_lst)
    # validate
    validate_cloud_sql_resource_name(name)
    validation.validate_path_value_lst(path_value_lst)
    # logic
    await asyncio.sleep(0)
    project, _, instance_name = _sql_fqn_components(name)
    await asyncio.sleep(0)
    update_request = xpath.create_dict_based_on_path_value_lst(path_value_lst)
    try:
        request = _sql_instances().patch(project=project, instance=instance_name, body=update_request)
        await asyncio.sleep(0)
        result = request.execute()
        await asyncio.sleep(0)
    except Exception as err:
        raise CloudSqlServiceError(
            f"Could not update instance '{name}' with '{path_value_lst}'. Request: {request}. Error: {err}"
        ) from err
    _LOGGER.info(
        "Update request for instance %s with %s sent.",
        name,
        path_value_lst,
    )
    return result
