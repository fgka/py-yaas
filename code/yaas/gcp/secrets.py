# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP `Secret Manager`_ entry point

.. _Secret Manager: https://cloud.google.com/secret-manager/docs/quickstart#secretmanager-quickstart-python
"""
# pylint: enable=line-too-long
from typing import List, Optional

import cachetools

from google.cloud import secretmanager

from yaas import const, logger
from yaas.gcp import resource_name, secrets_const

_LOGGER = logger.get(__name__)


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
        version = secrets_const.DEFAULT_GCP_SECRET_VERSION
    return secrets_const.GCP_SECRET_NAME_TMPL.format(
        project_id=project_id, secret_id=secret_id, version=version
    )


async def get(secret_name: str) -> str:
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
    _LOGGER.info("Retrieving secret <%s>", secret_name)
    try:
        response = await _secret_client().access_secret_version(
            request={"name": secret_name}
        )
    except Exception as err:
        msg = f"Could not retrieve secret <{secret_name}>. Error: {err}"
        _LOGGER.critical(msg)
        raise SecretManagerAccessError(msg) from err
    return response.payload.data.decode(const.ENCODING_UTF8)


@cachetools.cached(cache=cachetools.LRUCache(maxsize=1))
def _secret_client() -> secretmanager.SecretManagerServiceAsyncClient:
    return secretmanager.SecretManagerServiceAsyncClient()


def validate_secret_resource_name(
    value: str, *, raise_if_invalid: bool = True
) -> List[str]:
    """
    Validates the ``value`` against the pattern:
        "projects/my-project-123/secrets/my-secret/versions/my-version".

    Args:
        value: Secret resource name to be validated.
        raise_if_invalid: if :py:obj:`True` will raise exception if ``value`` is not valid.

    Returns:
        If ``raise_if_invalid`` if :py:obj:`False` will contain all reasons
            why the validation failed.
    """
    return resource_name.validate_resource_name(
        value=value,
        tokens=secrets_const.SECRET_NAME_TOKENS,
        raise_if_invalid=raise_if_invalid,
    )


async def put(*, secret_name: str, content: str) -> str:
    """
    Puts a secret, by name.

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>`
        content: secret content.
    Returns:
        The secret full name, with version.
    """
    if not isinstance(secret_name, str) or not secret_name:
        raise SecretManagerAccessError(
            f"Secret name must be a non-empty string. Got: <{secret_name}>({type(secret_name)})"
        )
    if not isinstance(content, str):
        raise SecretManagerAccessError(
            f"Content must be a string. Got: <{content}>({type(content)})"
        )
    _LOGGER.info("Adding a version to secret <%s>", secret_name)
    try:
        request = {
            "parent": secret_name,
            "payload": {"data": content.encode(const.ENCODING_UTF8)},
        }
        response = await _secret_client().add_secret_version(request=request)
    except Exception as err:
        msg = f"Could not retrieve secret <{secret_name}>. Error: {err}"
        _LOGGER.critical(msg)
        raise SecretManagerAccessError(msg) from err
    return response.name
