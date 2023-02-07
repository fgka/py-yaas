# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP `Cloud Run`_ entry point focused on control plane APIs.

.. _Cloud Run: https://cloud.google.com/python/docs/reference/run/latest
"""
# pylint: enable=line-too-long
import asyncio
from datetime import datetime
from typing import Any, List, Optional, Tuple

from google.cloud import run_v2

from yaas import logger
from yaas.gcp import cloud_run_const, resource_name

_LOGGER = logger.get(__name__)

_CLOUD_RUN_REVISION_TMPL: str = "{}-scaler-{}"


class CloudRunServiceError(Exception):
    """
    To encapsulate all exceptions operating on CloudRun.
    """


async def get_service(name: str) -> run_v2.Service:
    # pylint: disable=line-too-long
    """
    Wrapper for :py:meth:`run_v2.ServicesClient.get_service` (`documentation`_).

    Args:
        name: full service name, e.g.:
            `projects/my-project-123/locations/my-location-123/services/my-service-123`.

    Returns:
        Service

    Raises:
        py:class:`CloudRunServiceError` any error accessing the CloudRun control plane.

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.services.services.ServicesClient#google_cloud_run_v2_services_services_ServicesClient_get_service
    .. _x-path: https://en.wikipedia.org/wiki/XPath
    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Getting service <%s>", name)
    # validate
    validate_cloud_run_resource_name(name)
    # get service definition
    await asyncio.sleep(0)
    try:
        result = _run_client().get_service(request={"name": name})
        await asyncio.sleep(0)
    except Exception as err:  # pylint: disable=broad-except
        raise CloudRunServiceError(
            f"Could not retrieve service <{name}>. Error: {err}"
        ) from err
    return result


async def can_be_deployed(name: str) -> Tuple[bool, str]:
    # pylint: disable=line-too-long
    """
    A wrapper around :py:func:`get_service` and returning ``NOT reconciling`` field.
    Check ``reconciling`` in `Service`_ definition.

    Args:
        name:

    Returns:
        A tuple in the form ``(<can_enact: bool>, <reason for False: str>)``.

    .. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    # pylint: enable=line-too-long
    reason = None
    _LOGGER.debug("Checking readiness of service <%s>", name)
    try:
        # service
        service = await get_service(name)
        # checking reconciling
        if service.reconciling:
            reason = f"Service <{name}> is reconciling, try again later."
    except Exception as err:  # pylint: disable=broad-except
        reason = f"Could not retrieve service with name <{name}>. Error: {err}"
        _LOGGER.exception(reason)
    return reason is None, reason


def validate_cloud_run_resource_name(
    value: str, *, raise_if_invalid: bool = True
) -> List[str]:
    """
    Validates the ``value`` against the pattern:
        "projects/my-project-123/locations/my-location-123/services/my-service-123".

    Args:
        value: Could Run resource name to be validated.
        raise_if_invalid: if :py:obj:`True` will raise exception if ``value`` is not valid.

    Returns:
        If ``raise_if_invalid`` if :py:obj:`False` will contain all reasons
            why the validation failed.
    """
    return resource_name.validate_resource_name(
        value=value,
        tokens=cloud_run_const.CLOUD_RUN_NAME_TOKENS,
        raise_if_invalid=raise_if_invalid,
    )


def _run_client() -> run_v2.ServicesClient:
    return run_v2.ServicesClient()


async def update_service(
    *, name: str, path: str, value: Optional[Any]
) -> run_v2.Service:
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
    validate_cloud_run_resource_name(name)
    if not isinstance(path, str) or not path.strip():
        raise TypeError(
            f"Path argument must be a non-empty {str.__name__}. Got: <{path}>({type(path)}"
        )
    path = path.strip()
    # get service
    service = await get_service(name)
    # update service
    service = _update_service_revision(
        _clean_service_for_update_request(
            _set_service_value_by_path(service, path, value)
        )
    )
    request = _create_update_request(service)
    await asyncio.sleep(0)
    try:
        operation = _run_client().update_service(request=request)
        await asyncio.sleep(0)
        result = operation.result()
    except Exception as err:
        raise CloudRunServiceError(
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
) -> run_v2.UpdateServiceRequest:
    """For testing"""
    return run_v2.UpdateServiceRequest(service=service, **kwargs)


def _set_service_value_by_path(service: Any, path: str, value: Any) -> Any:
    # pylint: disable=line-too-long
    """
    Set `value` on :py:class:`run_v2.Service` (`documentation`_) based on `path`.
    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    # pylint: enable=line-too-long
    node, attr_name = _get_parent_node_attribute_based_on_path(service, path)
    setattr(node, attr_name, value)
    return service


def _get_parent_node_attribute_based_on_path(value: Any, path: str) -> Tuple[Any, str]:
    result = value
    split_path = path.split(cloud_run_const.REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        result = getattr(result, entry)
    return result, split_path[-1]


def _clean_service_for_update_request(value: Any) -> Any:
    for path in cloud_run_const.CLOUD_RUN_UPDATE_REQUEST_SERVICE_PATHS_TO_REMOVE:
        node, attr_name = _get_parent_node_attribute_based_on_path(value, path)
        setattr(node, attr_name, None)
    return value


def _update_service_revision(service: Any) -> Any:
    node, attr_name = _get_parent_node_attribute_based_on_path(
        service, cloud_run_const.CLOUD_RUN_SERVICE_REVISION_PATH
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
    node, attr_name = _get_parent_node_attribute_based_on_path(service, path)
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
