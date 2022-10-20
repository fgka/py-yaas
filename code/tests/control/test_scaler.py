# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,no-self-use,using-constant-test
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods, redefined-builtin
# type: ignore
from datetime import datetime
from typing import Any

import attrs

import pytest

from yaas import const
from yaas.cal import scaling_target
from yaas.control import scaler

_TEST_CLOUD_RUN_TARGET_VALUE: int = 10
_TEST_CLOUD_RUN_RESOURCE_NAME: str = (
    "projects/my-project-123/locations/my-location-123/services/my-service-123"
)
_TEST_CLOUD_RUN_SCALING_TARGET: scaling_target.BaseScalingTarget = (
    scaling_target.CloudRunScalingTarget(
        name=_TEST_CLOUD_RUN_RESOURCE_NAME,
        start=datetime.now(),
        scaling_value=_TEST_CLOUD_RUN_TARGET_VALUE,
    )
)


def test__apply_cloud_run_ok(monkeypatch):
    # Given
    update_args = None
    update_result = None

    def mocked_update_service(*args) -> Any:
        nonlocal update_args
        update_args = args
        return update_result

    monkeypatch.setattr(scaler.cloud_run, "update_service", mocked_update_service)
    # When
    result = scaler._apply_cloud_run(_TEST_CLOUD_RUN_SCALING_TARGET)
    # Then
    assert result == update_result
    assert update_args
    assert len(update_args) == 3
    name, path, value = update_args
    assert name == _TEST_CLOUD_RUN_RESOURCE_NAME
    assert path == const.CLOUD_RUN_SERVICE_SCALING_TARGET_PARAM
    assert value == _TEST_CLOUD_RUN_TARGET_VALUE


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        {},
        attrs.asdict(_TEST_CLOUD_RUN_SCALING_TARGET),
    ],
)
def test_apply_nok_type_error(value: scaling_target.BaseScalingTarget):
    # Given/When/Then
    with pytest.raises(TypeError):
        scaler.apply(value)


@attrs.define(**const.ATTRS_DEFAULTS)
class _TestScalingTarget(scaling_target.BaseScalingTarget):
    pass


def test_appy_nok_value_error():
    # Given
    value = _TestScalingTarget(name="name", start=datetime.now())
    # When/Then
    with pytest.raises(ValueError):
        scaler.apply(value)
