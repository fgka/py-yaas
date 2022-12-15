# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP `Secret Manager`_ entry point

.. _Secret Manager: https://cloud.google.com/secret-manager/docs/quickstart#secretmanager-quickstart-python
"""
# pylint: enable=line-too-long
from typing import Optional

import cachetools

from google.cloud import secretmanager

from yaas import const, logger

_LOGGER = logger.get(__name__)

_GCP_SECRET_NAME_TMPL: str = (
    "projects/{project_id}/secrets/{secret_id}/versions/{version}"
)
_DEFAULT_GCP_SECRET_VERSION: str = "latest"


class SecretManagerAccessError(Exception):
    """To code all Secret Manager errors"""


def name(project_id: str, secret_id: str, *, version: Optional[str] = None) -> str:
    """
    Build a canonical secret path in the format::
       projects/<<project id>>/secrets/<<secret id>>/versions/<<version>>

    Args:
        project_id:
        secret_id:
        version: Default value `latest`

    Returns:

    """
    # validate
    if not isinstance(project_id, str) or not project_id:
        raise TypeError(
            f"Project ID must be a non-empty string. Got: <{project_id}>({type(project_id)})"
        )
    if not isinstance(secret_id, str) or not secret_id:
        raise TypeError(
            f"Secret ID must be a non-empty string. Got: <{secret_id}>({type(secret_id)})"
        )
    # logic
    if not isinstance(version, str):
        version = _DEFAULT_GCP_SECRET_VERSION
    return _GCP_SECRET_NAME_TMPL.format(
        project_id=project_id, secret_id=secret_id, version=version
    )


def get(secret_name: str) -> str:
    """
    Retrieves a secret, by name.

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>/versions/<<version>>`
    Returns:
        Secret content
    """
    if not isinstance(secret_name, str) or not secret_name:
        raise SecretManagerAccessError(
            f"Secret name must be a non-empty string. Got: <{secret_name}>({type(secret_name)})"
        )
    client = _secret_client()
    _LOGGER.info("Retrieving secret <%s>", secret_name)
    try:
        response = client.access_secret_version(request={"name": secret_name})
    except Exception as err:
        msg = f"Could not retrieve secret <{secret_name}>. Error: {err}"
        _LOGGER.critical(msg)
        raise SecretManagerAccessError(msg) from err
    return response.payload.data.decode(const.ENCODING_UTF8)


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _secret_client() -> secretmanager.SecretManagerServiceClient:
    return secretmanager.SecretManagerServiceClient()
