# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""GCP `Secret Manager`_ entry point.

**NOTE on ``async`` client**: It does not work well with threads, see: https://github.com/grpc/grpc/issues/25364

.. _Secret Manager: https://cloud.google.com/secret-manager/docs/quickstart#secretmanager-quickstart-python
"""
import asyncio
from typing import Callable, List, Optional

from google.cloud import secretmanager

from yaas_common import const, logger, preprocess
from yaas_gcp import resource_name, secrets_const

_LOGGER = logger.get(__name__)


class SecretManagerAccessError(Exception):
    """To code all Secret Manager errors."""


def name(project_id: str, secret_id: str, *, version: Optional[str] = None) -> str:
    """Build a canonical secret path in the format:: projects/<<project
    id>>/secrets/<<secret id>>/versions/<<version>>

    Args:
        project_id: project ID
        secret_id: secret ID
        version: Default value `latest`

    Returns:
    """
    # validate
    if not isinstance(project_id, str) or not project_id:
        raise TypeError(f"Project ID must be a non-empty string. Got: <{project_id}>({type(project_id)})")
    if not isinstance(secret_id, str) or not secret_id:
        raise TypeError(f"Secret ID must be a non-empty string. Got: <{secret_id}>({type(secret_id)})")
    # logic
    if not isinstance(version, str):
        version = secrets_const.DEFAULT_GCP_SECRET_VERSION
    return secrets_const.GCP_SECRET_NAME_TMPL.format(project_id=project_id, secret_id=secret_id, version=version)


async def list_versions(secret_name: str, *, include_destroyed_versions: bool = False) -> List[str]:
    """Will list all versions for the secret. Using following `API`_ and
    `filtering`_.

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>`
        include_destroyed_versions: include destroyed?

    .. _API: https://cloud.google.com/secret-manager/docs/view-secret-version
    .. _filtering: https://cloud.google.com/secret-manager/docs/filtering
    """
    _LOGGER.debug("Listing secret versions for <%s>", secret_name)
    # validate input
    secret_name = _validate_secret_name(secret_name)
    # logic
    secret_name = _secret_name_parent(secret_name)
    await asyncio.sleep(0)
    request = {"parent": secret_name}
    if not include_destroyed_versions:
        request["filter"] = "state:(ENABLED OR DISABLED)"
    try:
        result = [version.name for version in _secret_client().list_secret_versions(request=request)]
    except Exception as err:
        raise SecretManagerAccessError(f"Could not list secret versions for <{secret_name}>. Error: {err}") from err
    _LOGGER.info(
        "Listed secret versions for <%s>. There are <%d> versions.",
        secret_name,
        len(result),
    )
    return result


def _secret_name_parent(value: str) -> str:
    # secret_name: projects/<<project id>>/secrets/<<secret id>>/versions/<<version number>>
    if secrets_const.VERSION_SUB_STR in value:
        value = value.split(secrets_const.VERSION_SUB_STR)[0]
    # secret_name: projects/<<project id>>/secrets/<<secret id>>
    return value


async def exists(secret_name: str) -> bool:
    """Checks if a particular secret version exists. If the secret does not
    exist at all it will raise and exception, but will return :py:bool:`False`
    if the version does not exist or the secret is empty. Using following
    `API`_.

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>/versions/<<version>>`
    Returns:
        If the specific version exists.
    """
    _LOGGER.debug("Checking existence of secret <%s>", secret_name)
    # input validation
    secret_name = _validate_secret_name(secret_name)
    if secrets_const.VERSION_SUB_STR not in secret_name:
        raise ValueError(
            "Secret name must include versions "
            f"as in the pattern <{secrets_const.GCP_SECRET_NAME_TMPL}>. "
            f"Got: <{secret_name}>"
        )
    # logic
    version_names = await list_versions(secret_name)
    result = secret_name.endswith(secrets_const.LATEST_VERSION_SUFFIX) and version_names
    if not result:
        result = secret_name in version_names
    return result


async def get(secret_name: str) -> str:
    """Retrieves a secret, by name. Using following `API`_.

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>/versions/<<version>>`
    Returns:
        Secret content

    .. _API: https://cloud.google.com/secret-manager/docs/access-secret-version
    """
    secret_name = _validate_secret_name(secret_name)
    _LOGGER.debug("Retrieving secret <%s>", secret_name)
    await asyncio.sleep(0)
    try:
        response = _secret_client().access_secret_version(request={"name": secret_name})
        await asyncio.sleep(0)
    except Exception as err:
        msg = f"Could not retrieve secret <{secret_name}>. Error: {err}"
        _LOGGER.critical(msg)
        raise SecretManagerAccessError(msg) from err
    result = response.payload.data.decode(const.ENCODING_UTF8)
    _LOGGER.info("Retrieved secret <%s>", response.name)
    return result


def _validate_secret_name(value: str, *, if_version_missing_add_latest: bool = True) -> str:
    result = preprocess.string(value, "value")
    if if_version_missing_add_latest:
        if secrets_const.VERSION_SUB_STR not in value:
            result = value + secrets_const.LATEST_VERSION_SUFFIX
    return result


def _secret_client() -> secretmanager.SecretManagerServiceClient:
    return secretmanager.SecretManagerServiceClient()


def validate_secret_resource_name(value: str, *, raise_if_invalid: bool = True) -> List[str]:
    """Validates the ``value`` against the pattern: "projects/my-
    project-123/secrets/my-secret/versions/my-version".

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
    """Puts a secret, by name. Using following `API`_.

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>`
        content: secret content.
    Returns:
        The secret full name, with version.

    .. _API: https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets
    """
    _LOGGER.debug("Adding a version to secret <%s>", secret_name)
    # validate input
    secret_name = _validate_secret_name(secret_name, if_version_missing_add_latest=False)
    if not isinstance(content, str):
        raise SecretManagerAccessError(f"Content must be a string. Got: <{content}>({type(content)})")
    # logic
    secret_name = _secret_name_parent(secret_name)
    await asyncio.sleep(0)
    try:
        request = {
            "parent": secret_name,
            "payload": {"data": content.encode(const.ENCODING_UTF8)},
        }
        response = _secret_client().add_secret_version(request=request)
        await asyncio.sleep(0)
    except Exception as err:
        msg = f"Could not retrieve secret <{secret_name}>. Error: {err}"
        _LOGGER.critical(msg)
        raise SecretManagerAccessError(msg) from err
    result = response.name
    _LOGGER.info("Added version <%s>", result)
    return result


DEFAULT_AMOUNT_TO_KEEP: int = 2
MIN_AMOUNT_TO_KEEP: int = 1


async def clean_up(*, secret_name: str, amount_to_keep: Optional[int] = None) -> None:
    """Will remove all versions, except the latest and the newest in
    `amount_to_keep`. Example:

     - There are 50 versions, including latest;
     - `amount_to_keep = 2`.

    This means that after this there will be 3 versions:
     - `latest` = enabled;
     - `latest - 1` = disabled;
     - `latest - 2` = dsiabled;

    Args:
        secret_name: a secret name in the format:
            `projects/<<project id>>/secrets/<<secret id>>`
        amount_to_keep: how many old versions (besides `latest`) to keep

    Source: https://cloud.google.com/secret-manager/docs/view-secret-version
    """
    _LOGGER.debug(
        "Cleaning up secret <%s> and keeping <%d> older versions",
        secret_name,
        amount_to_keep,
    )
    # validate input
    secret_name = _validate_secret_name(secret_name, if_version_missing_add_latest=False)
    if not isinstance(amount_to_keep, int):
        amount_to_keep = DEFAULT_AMOUNT_TO_KEEP
    amount_to_keep = max(MIN_AMOUNT_TO_KEEP, amount_to_keep)
    # logic
    secret_name = _secret_name_parent(secret_name)
    version_names = await list_versions(secret_name)
    # version_numbers: <<version number>>
    version_numbers = sorted(
        [int(version_name.split("/")[-1]) for version_name in version_names],
        reverse=True,
    )
    # assuming 63 versions, amount_to_keep = 3
    # latest = 63
    # to_keep = [62, 61, 59]
    to_keep = version_numbers[1 : (amount_to_keep + 1)]
    await _disable_versions(secret_name, to_keep)
    # to_remove = [58, ..., 1]
    to_remove = version_numbers[(amount_to_keep + 1) :]
    await _remove_versions(secret_name, to_remove)
    _LOGGER.info(
        "Cleaned up secret <%s>, removing <%d> versions and disabling <%d>",
        secret_name,
        len(to_remove),
        len(to_keep),
    )


async def _disable_versions(secret_name: str, version_numbers: List[int]) -> None:
    """
    Source: https://cloud.google.com/secret-manager/docs/disable-secret-version
    """

    def disable_version(value: str) -> None:
        _LOGGER.debug("Disabling secret version: <%s>", value)
        response = _secret_client().disable_secret_version(request={"name": value})
        _LOGGER.debug("Disabled secret version: <%s>", response.name)

    _LOGGER.debug(
        "Disabling secret versions from <%s>. Versions to disable: <%s>",
        secret_name,
        version_numbers,
    )
    errors = await _apply_operation_on_versions(secret_name, version_numbers, disable_version)
    if errors:
        raise SecretManagerAccessError(
            f"Could not disable versions of secret <{secret_name}>. "
            f"Argument: <{version_numbers}>. "
            f"Error: {errors}"
        )
    _LOGGER.info(
        "Disabled secret versions from <%s>. Versions to disable: <%s>",
        secret_name,
        version_numbers,
    )


async def _apply_operation_on_versions(
    secret_name: str, version_numbers: List[int], operation: Callable[[str], None]
) -> List[str]:
    errors = []
    fqn_secret_name_prefix = f"{secret_name}/versions"
    for v_number in version_numbers:
        fqn_secret_name = f"{fqn_secret_name_prefix}/{v_number}"
        await asyncio.sleep(0)
        try:
            operation(fqn_secret_name)
        except Exception as err:  # pylint: disable=broad-except
            errors.append(
                f"Could not execute operation on secret <{fqn_secret_name}>. "
                f"Operation: <{operation}>. "
                f"Error: {err}",
            )
    return errors


async def _remove_versions(secret_name: str, version_numbers: List[int]) -> None:
    """
    Source: https://cloud.google.com/secret-manager/docs/destroy-secret-version
    """

    def remove_version(value: str) -> None:
        _LOGGER.debug("Removing secret version: <%s>", value)
        response = _secret_client().destroy_secret_version(request={"name": value})
        _LOGGER.debug("Removed secret version: <%s>", response.name)

    _LOGGER.debug(
        "Removing secret versions from <%s>. Versions to disable: <%s>",
        secret_name,
        version_numbers,
    )
    errors = await _apply_operation_on_versions(secret_name, version_numbers, remove_version)
    if errors:
        raise SecretManagerAccessError(
            f"Could not remove versions of secret <{secret_name}>. "
            f"Argument: <{version_numbers}>. "
            f"Error: {errors}"
        )
    _LOGGER.info(
        "Removed secret versions from <%s>. Versions disabled: <%s>",
        secret_name,
        version_numbers,
    )
