# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Dict, Tuple

import pytest

from yaas.dto import request, scaling
from yaas.scaler import base

from tests import common

_CALLED: Dict[str, bool] = {}


class _MyScalingCommand(scaling.ScalingCommand):
    def _is_parameter_valid(self, name: str, value: Any) -> None:
        _CALLED[_MyScalingCommand._is_parameter_valid.__name__] = True

    def _is_target_valid(self, name: str, value: Any) -> None:
        _CALLED[_MyScalingCommand._is_target_valid.__name__] = True


class TestScalingCommand:
    def test_ctor_ok(self):
        # Given/When
        obj = _MyScalingCommand(parameter="TEST_PARAMETER", target="TEST_TARGET")
        # Then
        assert obj is not None
        assert _CALLED.get(scaling.ScalingCommand._is_parameter_valid.__name__)
        assert _CALLED.get(scaling.ScalingCommand._is_target_valid.__name__)


class _MyScalingDefinition(common.MyScalingDefinition):
    def _is_resource_valid(self, name: str, value: str) -> None:
        _CALLED[_MyScalingDefinition._is_resource_valid.__name__] = True


class TestScalingDefinition:
    def test_from_request_ok(self):
        # Given
        req, obj = _create_request_and_definition(
            scaling_definition_cls=_MyScalingDefinition
        )
        # when
        result = _MyScalingDefinition.from_request(req)
        # Then
        assert result is not None
        assert obj == result
        assert _CALLED.get(scaling.ScalingDefinition._is_resource_valid.__name__)


def _create_request_and_definition(
    *,
    topic: str = "TEST_TOPIC",
    resource: str = "TEST_RESOURCE",
    parameter: str = "TEST_PARAMETER",
    target: str = "TEST_TARGET",
    timestamp_utc: int = 123,
    scaling_definition_cls: type = common.MyScalingDefinition,
) -> Tuple[request.ScaleRequest, scaling.ScalingDefinition]:
    command_str = f"{parameter} {target}"
    command = scaling.ScalingCommand(parameter=parameter, target=target)
    obj = scaling_definition_cls(
        resource=resource, command=command, timestamp_utc=timestamp_utc
    )
    req = common.create_scale_request(
        topic=topic,
        resource=obj.resource,
        command=command_str,
        timestamp_utc=timestamp_utc,
    )
    return req, obj


class TestScaler:
    def test_from_request_ok(self):
        # Given
        req, definition = _create_request_and_definition()
        # When
        result = common.MyScaler.from_request(req)
        # Then
        assert result is not None
        assert result.definition == definition
        assert not result.called.get(base.Scaler.can_enact.__name__)
        assert not result.called.get(base.Scaler._safe_enact.__name__)

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        req, _ = _create_request_and_definition()
        obj = common.MyScaler.from_request(req)
        obj._can_enact = True
        # When
        result = await obj.enact()
        # Then
        assert result
        assert obj.called.get(base.Scaler.can_enact.__name__)
        assert obj.called.get(base.Scaler._safe_enact.__name__)

    @pytest.mark.asyncio
    async def test_enact_nok(self):
        # Given
        req, _ = _create_request_and_definition()
        obj = common.MyScaler.from_request(req)
        obj._can_enact = False
        obj._reason = "TEST_REASON"
        # When
        result = await obj.enact()
        # Then
        assert not result
        assert obj.called.get(base.Scaler.can_enact.__name__)
        assert not obj.called.get(base.Scaler._safe_enact.__name__)


class TestCategoryScaleRequestParser:
    def setup(self):
        self.obj = common.MyCategoryScaleRequestParser()

    def test_scaler_ok(self):
        # Given
        req, _ = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name
        )
        # When
        scaler = self.obj.scaler(req)
        # Then
        assert scaler is not None
        assert self.obj.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
        assert self.obj.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
        assert common.MyCategoryScaleRequestParser.cls_called.get(
            common.MyCategoryScaleRequestParser.supported_categories.__name__
        )
        # Then: filter
        filter_req = self.obj.obj_called.get(
            base.CategoryScaleRequestParser._filter_requests.__name__
        )
        assert len(filter_req) == 1
        assert list(filter_req)[0] == common.MyScalingDefinition.from_request(req)

    def test_is_supported_ok(self):
        for item in common.MyCategoryType:
            assert self.obj.is_supported(item.name)
            assert not self.obj.is_supported(item.value)

    def test_scaler_ok_no_singulate(self):
        # Given
        req, _ = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name
        )
        # When
        scaler = self.obj.scaler(req, singulate_if_only_one=False)
        # Then
        assert isinstance(scaler, list)
        assert len(scaler) == 1
        assert isinstance(scaler[0], base.Scaler)

    def test_scaler_ok_multiple(self):
        # Given
        req, _ = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name
        )
        amount = 3
        value = [req] * amount
        # When
        scaler_lst = self.obj.scaler(*value)
        # Then
        assert isinstance(scaler_lst, list)
        assert len(scaler_lst) == amount
        for val in scaler_lst:
            assert isinstance(val, base.Scaler)
        assert self.obj.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
        assert common.MyCategoryScaleRequestParser.cls_called.get(
            base.CategoryScaleRequestParser.supported_categories.__name__
        )
        # Then: filter
        filter_req = self.obj.obj_called.get(
            base.CategoryScaleRequestParser._filter_requests.__name__
        )
        assert len(filter_req) == amount
        for f_req in filter_req:
            assert f_req == common.MyScalingDefinition.from_request(req)

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        req, _ = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name
        )
        # When
        result, scaler = await self.obj.enact(req)
        # Then
        assert isinstance(result, bool)
        assert isinstance(scaler, base.Scaler)
        assert scaler.called.get(base.Scaler.can_enact.__name__)
        assert scaler.called.get(base.Scaler._safe_enact.__name__)

    @pytest.mark.asyncio
    async def test_enact_ok_no_singulate(self):
        # Given
        req, _ = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name
        )
        # When
        result = await self.obj.enact(req, singulate_if_only_one=False)
        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        for res, scaler in result:
            assert isinstance(res, bool)
            assert isinstance(scaler, base.Scaler)

    @pytest.mark.asyncio
    async def test_enact_ok_multiple(self):
        # Given
        req, _ = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name
        )
        amount = 3
        # When
        result = await self.obj.enact(*[req] * amount)
        # Then
        assert isinstance(result, list)
        assert len(result) == amount
        for res, scaler in result:
            assert isinstance(res, bool)
            assert isinstance(scaler, base.Scaler)
