# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP `Cloud Run`_ entry point focused on control plane APIs.

.. _Secret Manager: https://cloud.google.com/python/docs/reference/run/latest
"""
# pylint: enable=line-too-long
from typing import Any, Dict, Optional

import cachetools

from google.cloud import run_v2

from yaas import const, logger

_LOGGER = logger.get(__name__)


def update_service(name: str, path: str, value: Optional[Any]) -> Any:
    # pylint: disable=line-too-long
    """
    Wrapper for :py:meth:`run_v2.ServicesClient.update_service` (`documentation`_)
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
    if not const.CLOUD_RUN_NAME_REGEX.match(name):
        raise TypeError(
            "Name argument must be a full Google Cloud Cloud Run resource name. "
            f"Got: <{name}>({type(name)}. Validating pattern: {const.CLOUD_RUN_NAME_REGEX}"
        )
    if not isinstance(path, str) or not path.strip():
        raise TypeError(
            f"Path argument must be a non-empty {str.__name__}. Got: <{path}>({type(path)}"
        )
    path = path.strip()
    # update
    service = _update_service_definition(name, path, value)
    request = dict(service=service)
    operation = _run_client().update_service(request=request)
    result = operation.result()
    _LOGGER.info(
        "Update request for service %s with param %s = %s sent. Result: %s",
        name,
        path,
        value,
        result,
    )
    return result


def _update_service_definition(name: str, path: str, value: Any) -> Dict[str, Any]:
    # pylint: disable=line-too-long
    """
    Dictionary version of :py:class:`run_v2.Service` (`documentation`_).
    Args:
        path:
        value:

    Returns:

    .. _documentation: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
    """
    # pylint: enable=line-too-long
    name_dict = _dict_from_path(const.CLOUD_RUN_UPDATE_REQUEST_NAME_PATH, name)
    scaling_dict = _dict_from_path(path, value)
    return {**scaling_dict, **name_dict}


def _dict_from_path(path: str, value: Any) -> Dict[str, Any]:
    """
    Builds a dictionary from `path` with `value`. E.g.::
        path = "root.node.sub_node"
        value = 123
        print(_dict_from_path(path, value))
        >> {"root": {"node": {"sub_node": 123}}}
    Args:
        path:
        value:

    Returns:

    """
    result = {}
    node = result
    split_path = path.split(const.REQUEST_PATH_SEP)
    for entry in split_path[:-1]:
        node[entry] = {}
        node = node[entry]
    node[split_path[-1]] = value
    return result


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _run_client() -> run_v2.ServicesClient:
    return run_v2.ServicesClient()
