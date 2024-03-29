# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,invalid-name
# type: ignore
import pytest

from yaas_gcp import resource_regex
from yaas_scaler import resource_name_parser

_TEST_RESOURCE_CLOUD_RUN_PROJECT: str = "my_project"
_TEST_RESOURCE_CLOUD_RUN_LOCATION: str = "my_location"
_TEST_RESOURCE_CLOUD_RUN_SERVICE: str = "my_service"
# pylint: disable=line-too-long
_TEST_RESOURCE_CLOUD_RUN_CANONICAL: str = f"projects/{_TEST_RESOURCE_CLOUD_RUN_PROJECT}/locations/{_TEST_RESOURCE_CLOUD_RUN_LOCATION}/services/{_TEST_RESOURCE_CLOUD_RUN_SERVICE}"
_TEST_RESOURCE_CLOUD_RUN_SIMPLIFIED: str = f"CloudRun {_TEST_RESOURCE_CLOUD_RUN_SERVICE} @ {_TEST_RESOURCE_CLOUD_RUN_PROJECT} {_TEST_RESOURCE_CLOUD_RUN_LOCATION}"
# pylint: enable=line-too-long


@pytest.mark.parametrize(
    "resource,expected_type,expected_canonical",
    [
        (
            _TEST_RESOURCE_CLOUD_RUN_CANONICAL,
            resource_regex.ResourceType.CLOUD_RUN,
            _TEST_RESOURCE_CLOUD_RUN_CANONICAL,
        ),
        (
            _TEST_RESOURCE_CLOUD_RUN_SIMPLIFIED,
            resource_regex.ResourceType.CLOUD_RUN,
            _TEST_RESOURCE_CLOUD_RUN_CANONICAL,
        ),
    ],
)
def test_canonical_resource_type_and_name_ok_cloud_run(
    resource: str, expected_type: resource_regex.ResourceType, expected_canonical
):
    (
        resource_type,
        canonical_str,
    ) = resource_name_parser.canonical_resource_type_and_name(resource)
    # Then
    assert resource_type == expected_type
    assert canonical_str == expected_canonical


# pylint: disable=line-too-long
@pytest.mark.parametrize(
    "resource",
    [
        None,
        "",
        [],
        {},
        f"projects/{_TEST_RESOURCE_CLOUD_RUN_PROJECT}/locations/{_TEST_RESOURCE_CLOUD_RUN_LOCATION}/services/",
        f"projects/{_TEST_RESOURCE_CLOUD_RUN_PROJECT}/locations//services/{_TEST_RESOURCE_CLOUD_RUN_SERVICE}",
        f"projects//locations/{_TEST_RESOURCE_CLOUD_RUN_LOCATION}/services/{_TEST_RESOURCE_CLOUD_RUN_SERVICE}",
        f"/{_TEST_RESOURCE_CLOUD_RUN_PROJECT}/locations/{_TEST_RESOURCE_CLOUD_RUN_LOCATION}/services/{_TEST_RESOURCE_CLOUD_RUN_SERVICE}",
        f"CloudRun {_TEST_RESOURCE_CLOUD_RUN_SERVICE} @ {_TEST_RESOURCE_CLOUD_RUN_PROJECT} ",
        f"CloudRun {_TEST_RESOURCE_CLOUD_RUN_SERVICE} @  {_TEST_RESOURCE_CLOUD_RUN_LOCATION}",
        f"CloudRun  @ {_TEST_RESOURCE_CLOUD_RUN_PROJECT} {_TEST_RESOURCE_CLOUD_RUN_LOCATION}",
        f" {_TEST_RESOURCE_CLOUD_RUN_SERVICE} @ {_TEST_RESOURCE_CLOUD_RUN_PROJECT} {_TEST_RESOURCE_CLOUD_RUN_LOCATION}",
    ],
)
# pylint: enable=line-too-long
def test_canonical_resource_type_and_name_nok_cloud_run(resource: str):
    (
        resource_type,
        canonical_str,
    ) = resource_name_parser.canonical_resource_type_and_name(resource)
    # Then
    assert resource_type is None
    assert canonical_str is None
