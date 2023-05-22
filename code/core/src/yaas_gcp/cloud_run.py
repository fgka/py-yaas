# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCP `Cloud Run`_ entry point focused on control plane APIs.

.. _Cloud Run: https://cloud.google.com/python/docs/reference/run/latest
"""
import asyncio
from datetime import datetime
from typing import Any, List, Optional, Tuple

from google.cloud import run_v2

from yaas_common import logger, validation, xpath
from yaas_gcp import cloud_run_const, resource_name

_LOGGER = logger.get(__name__)

_CLOUD_RUN_REVISION_TMPL: str = "{}-scaler-{}"


class CloudRunServiceError(Exception):
    """To encapsulate all exceptions operating on Cloud Run."""


async def get_service(name: str) -> run_v2.Service:
    # pylint: disable=line-too-long
    """Wrapper for :py:meth:`run_v2.ServicesClient.get_service`
    (`documentation`_).

    Args:
        name: full service name, e.g.:
            `projects/my-project-123/locations/my-location-123/services/my-service-123`.

    Returns:
        Service

    Raises:
        CloudRunServiceError: any error accessing the CloudRun control plane.

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.services.services.ServicesClient#google_cloud_run_v2_services_services_ServicesClient_get_service
    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Getting service '%s'", name)
    # validate
    validate_cloud_run_resource_name(name)
    # get service definition
    await asyncio.sleep(0)
    try:
        result = _run_client().get_service(request={"name": name})
        await asyncio.sleep(0)
    except Exception as err:
        raise CloudRunServiceError(f"Could not retrieve service '{name}'. Error: {err}") from err
    return result


async def can_be_deployed(name: str) -> Tuple[bool, str]:
    """A wrapper around :py:func:`get_service` and returning ``NOT
    reconciling`` field. Check ``reconciling`` in `Service`_ definition.

    Args:
        name:

    Returns:
        A tuple in the form ``('can_enact: bool', 'reason for False: str')``.

    .. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    reason = None
    _LOGGER.debug("Checking readiness of service '%s'", name)
    try:
        # service
        service = await get_service(name)
        # checking reconciling
        if service.reconciling:
            reason = f"Service '{name}' is reconciling, try again later."
    except Exception as err:  # pylint: disable=broad-except
        reason = f"Could not retrieve service with name '{name}'. Error: {err}"
        _LOGGER.exception(reason)
    return reason is None, reason


def validate_cloud_run_resource_name(  # pylint: disable=invalid-name
    value: str, *, raise_if_invalid: bool = True
) -> List[str]:
    """Validates the ``value`` against the pattern: "projects/my-
    project-123/locations/my-location-123/services/my-service-123".

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


async def update_service(*, name: str, path_value_lst: List[Tuple[str, Optional[Any]]]) -> run_v2.Service:
    # pylint: disable=line-too-long
    """Wrapper for :py:meth:`run_v2.ServicesClient.update_service`
    (`documentation`_ and `API`_). The `path_value_lst` is a list of :py:class:`tuple` and
    has the following format: ``[(<path>,<value>,)]`` where:

        - ``path`` follows a simple `x-path`_ like path to the value
            to be updated in the Cloud Run service.
        - ``value`` the, optional, value that the attribute should assume.

    Args:
        name: full service name, e.g.:
            `projects/my-project-123/locations/my-location-123/services/my-service-123`.
        path_value_lst: list of tuples ``[(<path>,<value>,)]``

    Returns:
        Updated Cloud Run service.

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.services.services.ServicesClient#google_cloud_run_v2_services_services_ServicesClient_update_service
    .. _API: https://cloud.google.com/run/docs/reference/rpc/google.cloud.run.v2#google.cloud.run.v2.Services.UpdateService
    .. _x-path: https://en.wikipedia.org/wiki/XPath
    """
    # pylint: enable=line-too-long
    _LOGGER.debug("Updating service '%s' with '%s'", name, path_value_lst)
    # validate
    validate_cloud_run_resource_name(name)
    validation.validate_path_value_lst(path_value_lst)
    # logic
    # get service
    service = await get_service(name)
    # apply all changes
    for path, value in path_value_lst:
        service = _set_service_value_by_path(service, path, value)
    # create request
    service = _update_service_revision(_clean_service_for_update_request(service))
    request = _create_update_request(service)
    await asyncio.sleep(0)
    # apply update
    try:
        operation = _run_client().update_service(request=request)
        await asyncio.sleep(0)
        result = operation.result()
    except Exception as err:
        raise CloudRunServiceError(
            f"Could not update service '{name}' with '{path_value_lst}'. Request: {request}. Error: {err}"
        ) from err
    # done
    _LOGGER.info(
        "Update request for service %s with '%s'.",
        name,
        path_value_lst,
    )
    # validate
    for path, value in path_value_lst:
        _validate_service(result, path, value)
    #
    return result


def _create_update_request(service: run_v2.Service, **kwargs) -> run_v2.UpdateServiceRequest:
    """For testing."""
    return run_v2.UpdateServiceRequest(service=service, **kwargs)


def _set_service_value_by_path(service: Any, path: str, value: Any) -> Any:
    """Set `value` on :py:class:`run_v2.Service` (`documentation`_) based on
    `path`.

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    node, attr_name = xpath.get_parent_node_based_on_path(service, path)
    setattr(node, attr_name, value)
    return service


def _clean_service_for_update_request(value: Any) -> Any:  # pylint: disable=invalid-name
    for path in cloud_run_const.CLOUD_RUN_UPDATE_REQUEST_SERVICE_PATHS_TO_REMOVE:
        node, attr_name = xpath.get_parent_node_based_on_path(value, path)
        setattr(node, attr_name, None)
    return value


def _update_service_revision(service: Any) -> Any:
    node, attr_name = xpath.get_parent_node_based_on_path(service, cloud_run_const.CLOUD_RUN_SERVICE_REVISION_PATH)
    revision = _create_revision(service.name)
    setattr(node, attr_name, revision)
    return service


def _create_revision(name: str) -> str:
    simple_name = name.split("/")[-1]
    ts_int = int(datetime.utcnow().timestamp())
    return _CLOUD_RUN_REVISION_TMPL.format(simple_name, ts_int)


def _validate_service(service: Any, path: str, value: Any, raise_if_invalid: bool = True) -> Any:
    """Get current `value` from :py:class:`run_v2.Service` (`documentation`_)
    based on `path` and compare to desired/target `value`.

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    node, attr_name = xpath.get_parent_node_based_on_path(service, path)
    current = getattr(node, attr_name)
    if current != value:
        msg = f"Current value '{current}' is not desired value '{value}' for path '{path}' in '{service.name}'"
        if raise_if_invalid:
            raise RuntimeError(msg)
        _LOGGER.error(msg)
    return service
