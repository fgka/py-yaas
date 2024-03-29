# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,protected-access
# pylint: disable=attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Dict, Tuple

import pytest

from tests import common
from yaas_common import request
from yaas_scaler import base, scaling

_CALLED: Dict[str, bool] = {}


class _MyScalingCommand(scaling.ScalingCommand):
    def _is_parameter_value_valid(self, value: Any) -> bool:
        _CALLED[_MyScalingCommand._is_parameter_value_valid.__name__] = True
        return True

    def _is_target_value_valid(self, value: Any) -> None:
        _CALLED[_MyScalingCommand._is_target_value_valid.__name__] = True
        return True


class TestScalingCommand:
    def test_ctor_ok(self):
        # Given/When
        obj = _MyScalingCommand(parameter="TEST_PARAMETER", target="TEST_TARGET")
        # Then
        assert obj is not None
        assert _CALLED.get(scaling.ScalingCommand._is_parameter_value_valid.__name__)
        assert _CALLED.get(scaling.ScalingCommand._is_target_value_valid.__name__)


class _MyScalingDefinition(common.MyScalingDefinition):
    def _is_resource_valid(self, value: str) -> bool:
        _CALLED[_MyScalingDefinition._is_resource_valid.__name__] = True
        return True


class TestScalingDefinition:
    def test_from_request_ok(self):
        # Given
        req, obj = _create_request_and_definition(scaling_definition_cls=_MyScalingDefinition)
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
    obj = scaling_definition_cls(resource=resource, command=command, timestamp_utc=timestamp_utc)
    req = common.create_scale_request(
        topic=topic,
        resource=obj.resource,
        command=command_str,
        timestamp_utc=timestamp_utc,
    )
    return req, obj


class TestScaler:
    def setup_method(self):
        self.request, self.definition = _create_request_and_definition()
        self.obj = common.MyScaler.from_request(self.request)
        self.obj.__class__.cls_called = {}

    def teardown_method(self):
        self.obj.__class__.cls_path = ""
        self.obj.__class__.cls_called = {}

    def test_from_request_ok(self):
        # Given/When
        result = common.MyScaler.from_request(self.request)
        # Then
        assert result is not None
        assert result.definitions[0] == self.definition
        assert not result.called.get(base.Scaler.can_enact.__name__)
        assert not result.called.get(base.Scaler._safe_enact.__name__)
        assert common.MyScaler.cls_called[base.ScalerPathBased.from_request.__name__][0] == self.request

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        self.obj._can_enact = True
        # When
        result = await self.obj.enact()
        # Then
        assert result
        assert self.obj.called.get(base.Scaler.can_enact.__name__)
        assert self.obj.called.get(base.Scaler._safe_enact.__name__)

    @pytest.mark.asyncio
    async def test_enact_nok(self):
        # Given
        self.obj._can_enact = False
        self.obj._reason = "TEST_REASON"
        # When
        result = await self.obj.enact()
        # Then
        assert not result
        assert self.obj.called.get(base.Scaler.can_enact.__name__)
        assert not self.obj.called.get(base.Scaler._safe_enact.__name__)


_TEST_SCALER_PATH: str = "TEST_PATH"


class TestScalerPathBased:
    def setup_method(self):
        self.request, self.definition = _create_request_and_definition()
        self.obj = common.MyScalerPathBased.from_request(self.request)
        self.obj.__class__.cls_path = _TEST_SCALER_PATH
        self.obj.__class__.cls_called = {}

    def teardown_method(self):
        self.obj.__class__.cls_path = ""
        self.obj.__class__.cls_called = {}

    def test_from_request_ok(self):
        # Given/When
        result = common.MyScalerPathBased.from_request(self.request)
        # Then
        assert result is not None
        assert result.definitions[0] == self.definition
        assert not result.called.get(base.Scaler.can_enact.__name__)
        assert not result.called.get(base.Scaler._safe_enact.__name__)
        assert common.MyScalerPathBased.cls_called.get(base.ScalerPathBased.from_request.__name__)[0] == self.request

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        self.obj._can_enact = True
        # When
        result = await self.obj.enact()
        # Then
        assert result
        assert self.obj.called.get(base.Scaler.can_enact.__name__)
        # Then: _path_for_enact
        args_path_for_enact = common.MyScalerPathBased.cls_called.get(
            base.ScalerPathBased._get_enact_path_value.__name__
        )
        assert args_path_for_enact
        assert args_path_for_enact["resource"] == self.request.resource
        assert args_path_for_enact["field"] in self.request.command
        assert args_path_for_enact["target"] in self.request.command
        # Then: _enact_by_path
        args_enact_by_path = common.MyScalerPathBased.cls_called.get(
            base.ScalerPathBased._enact_by_path_value_lst.__name__
        )
        assert args_enact_by_path
        assert args_enact_by_path["resource"] == self.request.resource
        path_value_lst = args_enact_by_path["path_value_lst"]
        for path, value in path_value_lst:
            assert path == self.obj.__class__.cls_path
            assert value in self.request.command

    @pytest.mark.asyncio
    async def test_enact_nok(self):
        # Given
        self.obj._can_enact = False
        self.obj._reason = "TEST_REASON"
        # When
        result = await self.obj.enact()
        # Then
        assert not result
        assert self.obj.called.get(base.Scaler.can_enact.__name__)
        assert not self.obj.called.get(base.Scaler._safe_enact.__name__)


class TestCategoryScaleRequestParser:
    def setup_method(self):
        self.obj = common.MyCategoryScaleRequestParser()

    def test_scaler_ok(self):
        # Given
        req, _ = _create_request_and_definition(topic=common.MyCategoryType.CATEGORY_A.name)
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
        filter_req = self.obj.obj_called.get(base.CategoryScaleRequestParser._filter_requests.__name__).get("value")
        assert len(filter_req) == 1
        assert list(filter_req)[0] == common.MyScalingDefinition.from_request(req)

    def test_is_supported_ok(self):
        for item in common.MyCategoryType:
            assert self.obj.is_supported(item.name)
            assert not self.obj.is_supported(item.value)

    def test_scaler_ok_no_singulate(self):
        # Given
        req, _ = _create_request_and_definition(topic=common.MyCategoryType.CATEGORY_A.name)
        # When
        scaler = self.obj.scaler(req, singulate_if_only_one=False)
        # Then
        assert isinstance(scaler, list)
        assert len(scaler) == 1
        assert isinstance(scaler[0], base.Scaler)

    def test_scaler_ok_multiple_same_resource(self):
        # Given
        req, _ = _create_request_and_definition(topic=common.MyCategoryType.CATEGORY_A.name)
        amount = 3
        value = [req] * amount
        # When
        scaler_lst = self.obj.scaler(*value, singulate_if_only_one=False)
        # Then
        assert isinstance(scaler_lst, list)
        assert len(scaler_lst) == 1
        for val in scaler_lst:
            assert isinstance(val, base.Scaler)
        assert self.obj.obj_called.get(base.CategoryScaleRequestParser._scaler.__name__)
        assert common.MyCategoryScaleRequestParser.cls_called.get(
            base.CategoryScaleRequestParser.supported_categories.__name__
        )
        # Then: filter
        filter_req = self.obj.obj_called.get(base.CategoryScaleRequestParser._filter_requests.__name__).get("value")
        assert len(filter_req) == amount
        for f_req in filter_req:
            assert f_req == common.MyScalingDefinition.from_request(req)
        # Then: scaler
        scaler = scaler_lst[0]
        assert isinstance(scaler, base.Scaler)
        assert len(scaler.definitions) == amount

    @pytest.mark.asyncio
    async def test_enact_ok(self):
        # Given
        req, _ = _create_request_and_definition(topic=common.MyCategoryType.CATEGORY_A.name)
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
        req, _ = _create_request_and_definition(topic=common.MyCategoryType.CATEGORY_A.name)
        # When
        result = await self.obj.enact(req, singulate_if_only_one=False)
        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        for res, scaler in result:
            assert isinstance(res, bool)
            assert isinstance(scaler, base.Scaler)

    @pytest.mark.asyncio
    async def test_enact_ok_multiple_same_resource(self):
        # Given
        req, _ = _create_request_and_definition(topic=common.MyCategoryType.CATEGORY_A.name)
        amount = 3
        # When
        result = await self.obj.enact(*[req] * amount, singulate_if_only_one=False)
        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        res, scaler = result[0]
        assert isinstance(res, bool)
        # Then: scaler
        assert isinstance(scaler, base.Scaler)
        assert len(scaler.definitions) == amount


class TestCategoryScaleRequestParserWithFilter:
    def setup_method(self):
        self.obj = common.MyCategoryScaleRequestParserWithFilter()

    def test__filter_requests_ok(self):
        # Given
        _, old_def = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name,
            timestamp_utc=123,
        )
        _, new_def = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name,
            timestamp_utc=321,
        )
        # When
        result = self.obj._filter_requests(value=[{}, new_def, None, 123, old_def, ""], raise_if_invalid_request=False)
        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == new_def


class TestCategoryScaleRequestParserWithScaler:
    def setup_method(self):
        self.obj = common.MyCategoryScaleRequestParserWithScaler()

    @pytest.mark.parametrize(
        "value",
        [
            request.ScaleRequest(
                topic="standard",
                resource="locations/europe-west3/namespaces/yaas-test/services/integ-test",
                command="min_instances 10",
                timestamp_utc=123,
                original_json_event=None,
            ),
            request.ScaleRequest(
                topic="standard",
                resource="yaas-test:europe-west3:integ-test",
                command="instance_type db-custom-2-3840",
                timestamp_utc=123,
                original_json_event=None,
            ),
        ],
    )
    def test__to_scaling_definition_ok(self, value: request.ScaleRequest):
        # Given/When
        result = self.obj._to_scaling_definition([value])
        # Then
        assert result and len(result) == 1
        cmd = result[0]
        assert isinstance(cmd, common.MyScalingDefinition)
        assert cmd.resource == value.resource

    def test__scaling_definition_by_type_ok(self):
        # Given
        req_a, scaling_def_a = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name,
            timestamp_utc=123,
        )
        req_b, scaling_def_b = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_B.name,
            timestamp_utc=321,
        )
        value = [
            None,
            "",
            req_a,
            scaling_def_a,
            123,
            scaling_def_b,
            {},
            req_b,
            1.23,
        ]
        # When
        (
            errors,
            scale_def_by_type,
        ) = common.MyCategoryScaleRequestParserWithScaler._scaling_definition_by_type(value)
        # Then: errors
        assert isinstance(errors, list)
        assert len(errors) == len(value) - 2
        # Then: scale_def_by_type
        assert isinstance(scale_def_by_type, dict)
        assert len(scale_def_by_type) == 1
        scale_def_lst = scale_def_by_type.get(common.MyScalingDefinition)
        assert isinstance(scale_def_lst, list)
        assert len(scale_def_lst) == 2
        assert scaling_def_a in scale_def_lst
        assert scaling_def_b in scale_def_lst

    def test__scaler_ok(self):
        # Given
        req_a, scaling_def_a = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_A.name,
            timestamp_utc=123,
        )
        req_b, scaling_def_b = _create_request_and_definition(
            topic=common.MyCategoryType.CATEGORY_B.name,
            timestamp_utc=321,
        )
        value = [
            None,
            "",
            req_a,
            scaling_def_a,
            123,
            scaling_def_b,
            {},
            req_b,
            1.23,
        ]
        # When
        result = self.obj._scaler(value, raise_if_invalid_request=False)
        # Then
        assert isinstance(result, list)
        assert len(result) == 1
        res_scaler = result[0]
        assert isinstance(res_scaler, common.MyScaler)
        assert len(res_scaler.definitions) == 2
        assert scaling_def_a in res_scaler.definitions
        assert scaling_def_b in res_scaler.definitions
