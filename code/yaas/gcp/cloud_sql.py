# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP `Cloud SQL`_ entry point focused on control plane APIs.
The client is a generic client based on `discovery`_.
The full `REST API`_ documentation indicates how to use the generic client.

.. _Cloud SQL: https://github.com/googleapis/google-api-python-client
.. _discovery: https://googleapis.github.io/google-api-python-client/docs/start.html
.. _REST API: https://cloud.google.com/sql/docs/postgres/admin-api/rest
"""
# pylint: enable=line-too-long
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient import discovery

from yaas import logger
from yaas.gcp import cloud_sql_const
from yaas.scaler import resource_name_const
from yaas import xpath

_LOGGER = logger.get(__name__)

_CLOUD_RUN_REVISION_TMPL: str = "{}-scaler-{}"


class CloudSqlServiceError(Exception):
    """
    To encapsulate all exceptions operating on Cloud SQL.
    """


async def get_instance(value: str) -> Dict[str, Any]:
    # pylint: disable=line-too-long
    """
    Returns a :py:class:`dict` for the `DatabaseInstance`_
    Args:
        value: full instance name, e.g.:
            `my-project-123:my-location-123:my-instance-123`.

    Returns:
        Service

    Raises:
        py:class:`CloudSqlServiceError` any error accessing the Cloud SQL control plane.

    .. DatabaseInstance: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#DatabaseInstance
    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Getting instance <%s>", value)
    # validate
    project, _, instance_name = _sql_fqn_components(value)
    # get service definition
    await asyncio.sleep(0)
    try:
        request = _sql_client().instances().get(project=project, instance=instance_name)
        await asyncio.sleep(0)
        result = request.execute()
        await asyncio.sleep(0)
    except Exception as err:  # pylint: disable=broad-except
        raise CloudSqlServiceError(
            f"Could not retrieve service <{value}>. Error: {err}"
        ) from err
    return result


def _sql_fqn_components(value: str) -> Tuple[str, str, str]:
    """
    Components in the following fashion::
        project, location, instance_name = _sql_fqn_components(value)

    Args:
        value:

    Returns:

    """
    match = resource_name_const.FQN_CLOUD_SQL_TARGET_RESOURCE_REGEX.match(value)
    if match and len(match.groups()) == 3:
        project, location, instance_name = match.groups()
    else:
        raise ValueError(f"Instance name <{value}> is not a valid Cloud SQL resource name. Needs to comply with <{resource_name_const.FQN_CLOUD_SQL_TARGET_RESOURCE_REGEX}>")
    return project, location, instance_name


async def can_be_deployed(value: str) -> Tuple[bool, str]:
    # pylint: disable=line-too-long
    """
    A wrapper around :py:func:`get_instance` and returning :py:obj:`True`
        if `DatabaseInstance`_ state is `RUNNABLE`_.

    Args:
        value:

    Returns:
        A tuple in the form ``(<can_enact: bool>, <reason for False: str>)``.

    .. _DatabaseInstance: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#DatabaseInstance
    .. _RUNNABLE: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#SqlInstanceState
    """
    # pylint: enable=line-too-long
    reason = None
    _LOGGER.debug("Checking readiness of instance <%s>", value)
    try:
        # service
        instance = await get_instance(value)
        # checking reconciling
        if instance.get("status") != cloud_sql_const.CLOUD_SQL_STATE_OK:
            reason = f"Instance state <{value}> is reconciling, try again later."
    except Exception as err:  # pylint: disable=broad-except
        reason = f"Could not retrieve service with name <{value}>. Error: {err}"
        _LOGGER.exception(reason)
    return reason is None, reason


def validate_cloud_sql_resource_name(
    value: str, *, raise_if_invalid: bool = True
) -> List[str]:
    """
    Validates the ``value`` against the pattern:
        "my-project-123:my-location-123:my-instance-123".

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
    except Exception as err:
        if raise_if_invalid:
            raise err
        else:
            result.append(f"Could not parse instance name <{value}>. Error: {err}")
    return result


def _sql_client() -> discovery.Resource:
    """
    Based on: https://cloud.google.com/sql/docs/postgres/admin-api/libraries
    *NOTE*: all engines are the same way.
    """
    return discovery.build('sqladmin', 'v1beta4')


async def update_instance(
    *, name: str, path: str, value: Optional[Any]
) -> Dict[str, Any]:
    # pylint: disable=line-too-long
    """
    Wrapper for :py:meth:`run_v2.ServicesClient.update_service` (`documentation`_).

    Args:
        name: full service name, e.g.:
            `projects/my-project-123/locations/my-location-123/services/my-service-123`.
        path: simple `x-path`_ like path to the value to be updated in the Cloud Run service.
        value: what the end-node in `path` should contain.

    Returns:

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.services.services.ServicesClient#google_cloud_run_v2_services_services_ServicesClient_update_service
    .. _x-path: https://en.wikipedia.org/wiki/XPath
    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Updating service <%s> param <%s> with <%s>", name, path, value)
    # validate
    validate_cloud_sql_resource_name(name)
    if not isinstance(path, str) or not path.strip():
        raise TypeError(
            f"Path argument must be a non-empty {str.__name__}. Got: <{path}>({type(path)}"
        )
    path = path.strip()
    # get service
    service = await get_instance(name)
    # update service
    service = _update_service_revision(
        _clean_service_for_update_request(
            _set_service_value_by_path(service, path, value)
        )
    )
    request = _create_update_request(service)
    await asyncio.sleep(0)
    try:
        operation = _sql_client().update_service(request=request)
        await asyncio.sleep(0)
        result = operation.result()
    except Exception as err:
        raise CloudSqlServiceError(
            f"Could not update service <{name}> with <{path}> set to <{value}>. "
            f"Request: {request}. "
            f"Error: {err}"
        ) from err
    _LOGGER.info(
        "Update request for service %s with param %s = %s sent.",
        name,
        path,
        value,
    )
    return _validate_service(result, path, value)


def _create_update_request(
    service: run_v2.Service, **kwargs
) -> Dict[str, Any]:
    """For testing"""
    return run_v2.UpdateServiceRequest(service=service, **kwargs)


def _set_service_value_by_path(service: Any, path: str, value: Any) -> Any:
    # pylint: disable=line-too-long
    """
    Set `value` on :py:class:`run_v2.Service` (`documentation`_) based on `path`.
    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    # pylint: enable=line-too-long
    node, attr_name = xpath.get_parent_node_based_on_path(service, path)
    setattr(node, attr_name, value)
    return service



def _clean_service_for_update_request(value: Any) -> Any:
    for path in cloud_sql_const.CLOUD_RUN_UPDATE_REQUEST_SERVICE_PATHS_TO_REMOVE:
        node, attr_name = xpath.get_parent_node_based_on_path(value, path)
        setattr(node, attr_name, None)
    return value


def _update_service_revision(service: Any) -> Any:
    node, attr_name = xpath.get_parent_node_based_on_path(
        service, cloud_sql_const.CLOUD_RUN_SERVICE_REVISION_PATH
    )
    revision = _create_revision(service.name)
    setattr(node, attr_name, revision)
    return service


def _create_revision(name: str) -> str:
    simple_name = name.split("/")[-1]
    ts_int = int(datetime.utcnow().timestamp())
    return _CLOUD_RUN_REVISION_TMPL.format(simple_name, ts_int)


def _validate_service(
    service: Any, path: str, value: Any, raise_if_invalid: bool = True
) -> Any:
    # pylint: disable=line-too-long
    """
    Get current `value` from :py:class:`run_v2.Service` (`documentation`_) based on `path`
        and compare to desired/target `value`.
    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    # pylint: enable=line-too-long
    node, attr_name = xpath.get_parent_node_based_on_path(service, path)
    current = getattr(node, attr_name)
    if current != value:
        msg = (
            f"Current value <{current}> is not desired value <{value}> "
            f"for path <{path}> in <{service.name}>"
        )
        if raise_if_invalid:
            raise RuntimeError(msg)
        _LOGGER.error(msg)
    return service
