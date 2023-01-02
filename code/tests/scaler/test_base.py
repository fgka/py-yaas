# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pytest

from yaas.dto import request
from yaas.scaler import base

from tests import common

_CALLED: Dict[str, bool] = {}


class _MyScalingCommand(base.ScalingCommand):
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
        assert _CALLED.get(base.ScalingCommand._is_parameter_valid.__name__)
        assert _CALLED.get(base.ScalingCommand._is_target_valid.__name__)


class _MyScalingDefinition(base.ScalingDefinition):
    def _is_resource_valid(self, name: str, value: str) -> None:
        _CALLED[_MyScalingDefinition._is_resource_valid.__name__] = True

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "ScalingDefinition":
        param_target = value.command.split(" ")
        command = base.ScalingCommand(parameter=param_target[0], target=param_target[1])
        return _MyScalingDefinition(
            resource=value.resource,
            command=command,
            timestamp_utc=value.timestamp_utc,
        )


class TestScalingDefinition:
    def test_from_request_ok(self):
        # Given
        req, obj = _create_request_and_definition()
        # when
        result = _MyScalingDefinition.from_request(req)
        # Then
        assert result is not None
        assert obj == result
        assert _CALLED.get(base.ScalingDefinition._is_resource_valid.__name__)


def _create_request_and_definition(
    *,
    topic: str = "TEST_TOPIC",
    resource: str = "TEST_RESOURCE",
    parameter: str = "TEST_PARAMETER",
    target: str = "TEST_TARGET",
    timestamp_utc: int = 123,
) -> Tuple[request.ScaleRequest, base.ScalingDefinition]:
    command_str = f"{parameter} {target}"
    command = base.ScalingCommand(parameter=parameter, target=target)
    obj = _MyScalingDefinition(
        resource=resource, command=command, timestamp_utc=timestamp_utc
    )
    req = common.create_scale_request(
        topic=topic,
        resource=obj.resource,
        command=command_str,
        timestamp_utc=timestamp_utc,
    )
    return req, obj


class _MyScaler(base.Scaler):
    def __init__(
        self,
        definition: base.ScalingDefinition,
        can_enact: bool = True,
        reason: str = None,
    ) -> None:
        super().__init__(definition=definition)
        self._can_enact = can_enact
        self._reason = reason
        self.called = {}

    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "Scaler":
        definition = _MyScalingDefinition.from_request(value)
        return _MyScaler(definition=definition)

    async def _safe_enact(self) -> None:
        self.called[base.Scaler._safe_enact.__name__] = True

    async def can_enact(self) -> Tuple[bool, str]:
        self.called[base.Scaler.can_enact.__name__] = True
        return self._can_enact, self._reason


class TestScaler:
    def test_from_request_ok(self):
        # Given
        req, definition = _create_request_and_definition()
        # When
        result = _MyScaler.from_request(req)
        # Then
        assert result is not None
        assert result.definition == definition
        assert not result.called.get(base.Scaler.can_enact.__name__)
        assert not result.called.get(base.Scaler._safe_enact.__name__)

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        req, _ = _create_request_and_definition()
        obj = _MyScaler.from_request(req)
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
        obj = _MyScaler.from_request(req)
        obj._can_enact = False
        obj._reason = "TEST_REASON"
        # When
        result = await obj.enact()
        # Then
        assert not result
        assert obj.called.get(base.Scaler.can_enact.__name__)
        assert not obj.called.get(base.Scaler._safe_enact.__name__)


class _MyCategoryTypes(base.CategoryType):
    CATEGORY_A = "Category_1"
    CATEGORY_B = "Category_2"


class _MyCategoryScaleRequestParser(base.CategoryScaleRequestParser):

    cls_called = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_called = {}

    def _scaler(
        self,
        value: request.ScaleRequest,
        raise_if_invalid_request: Optional[bool] = True,
    ) -> base.Scaler:
        self.obj_called[base.CategoryScaleRequestParser._scaler.__name__] = True
        return _MyScaler.from_request(value)

    def _filter_requests(
        self,
        value: Iterable[request.ScaleRequest],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> List[request.ScaleRequest]:
        self.obj_called[
            base.CategoryScaleRequestParser._filter_requests.__name__
        ] = value
        return value

    @classmethod
    def supported_categories(cls) -> List[base.CategoryType]:
        cls.cls_called[
            base.CategoryScaleRequestParser.supported_categories.__name__
        ] = True
        return list(_MyCategoryTypes)


class TestCategoryScaleRequestParser:
    def setup(self):
        self.obj = _MyCategoryScaleRequestParser()

    def test_scaler_ok(self):
        # Given
        req, _ = _create_request_and_definition(topic=_MyCategoryTypes.CATEGORY_A.name)
        # When
        scaler = self.obj.scaler(req)
        # Then
        assert scaler is not None
        assert self.obj.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
        assert self.obj.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
        assert _MyCategoryScaleRequestParser.cls_called.get(
            _MyCategoryScaleRequestParser.supported_categories.__name__
        )
        # Then: filter
        filter_req = self.obj.obj_called.get(
            base.CategoryScaleRequestParser._filter_requests.__name__
        )
        assert len(filter_req) == 1
        assert list(filter_req)[0] == req

    def test_is_supported_ok(self):
        for item in _MyCategoryTypes:
            assert self.obj.is_supported(item.name)
            assert not self.obj.is_supported(item.value)

    def test_scaler_ok_no_singulate(self):
        # Given
        req, _ = _create_request_and_definition(topic=_MyCategoryTypes.CATEGORY_A.name)
        # When
        scaler = self.obj.scaler(req, singulate_if_only_one=False)
        # Then
        assert isinstance(scaler, list)
        assert len(scaler) == 1
        assert isinstance(scaler[0], base.Scaler)

    def test_scaler_ok_multiple(self):
        # Given
        req, _ = _create_request_and_definition(topic=_MyCategoryTypes.CATEGORY_A.name)
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
        assert _MyCategoryScaleRequestParser.cls_called.get(
            base.CategoryScaleRequestParser.supported_categories.__name__
        )
        # Then: filter
        filter_req = self.obj.obj_called.get(
            base.CategoryScaleRequestParser._filter_requests.__name__
        )
        assert len(filter_req) == amount
        for f_req in filter_req:
            assert f_req == req

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        req, _ = _create_request_and_definition(topic=_MyCategoryTypes.CATEGORY_A.name)
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
        req, _ = _create_request_and_definition(topic=_MyCategoryTypes.CATEGORY_A.name)
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
        req, _ = _create_request_and_definition(topic=_MyCategoryTypes.CATEGORY_A.name)
        amount = 3
        # When
        result = await self.obj.enact(*[req] * amount)
        # Then
        assert isinstance(result, list)
        assert len(result) == amount
        for res, scaler in result:
            assert isinstance(res, bool)
            assert isinstance(scaler, base.Scaler)
