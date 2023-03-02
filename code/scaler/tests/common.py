# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from yaas_common import request
from yaas_scaler import base, scaling

################
# ScaleRequest #
################


_TEST_SCALE_REQUEST_KWARGS: Dict[str, Any] = dict(
    topic="TEST_TOPIC",
    resource="TEST_RESOURCE",
    command="TEST_COMMAND 123",
    timestamp_utc=123,
    original_json_event="TEST_ORIGINAL_JSON_EVENT",
)


def create_scale_request(**kwargs) -> request.ScaleRequest:
    """
    Create a default :py:class:`request.ScaleRequest` using ``kwargs`` to overwrite defaults.

    Args:
        **kwargs:

    Returns:

    """
    scale_kwargs = {
        **_TEST_SCALE_REQUEST_KWARGS,
        **kwargs,
    }
    return request.ScaleRequest(**scale_kwargs)


##########
# Scaler #
##########


class MyScalingDefinition(scaling.ScalingDefinition):
    @classmethod
    def from_request(cls, value: request.ScaleRequest) -> "ScalingDefinition":
        param_target = value.command.split(" ")
        command = scaling.ScalingCommand(
            parameter=param_target[0], target=param_target[1]
        )
        return cls(
            resource=value.resource,
            command=command,
            timestamp_utc=value.timestamp_utc,
        )


class MyScaler(base.Scaler):
    cls_called: Dict[str, Any] = {}

    def __init__(
        self,
        *definition: scaling.ScalingDefinition,
        can_enact: bool = True,
        reason: str = None,
    ) -> None:
        super().__init__(*definition)
        self._can_enact = can_enact
        self._reason = reason
        self.called = {}

    def _is_resource_valid(self, value: str) -> bool:
        # pylint: disable=no-member
        self.called[base.Scaler._is_resource_valid.__name__] = value
        return True

    @classmethod
    def from_request(cls, *value: Tuple[request.ScaleRequest], **kwargs) -> "Scaler":
        cls.cls_called[base.Scaler.from_request.__name__] = value
        return MyScaler(*[MyScalingDefinition.from_request(val) for val in value])

    async def _safe_enact(self) -> None:
        self.called[base.Scaler._safe_enact.__name__] = True

    async def can_enact(self) -> Tuple[bool, str]:
        self.called[base.Scaler.can_enact.__name__] = True
        return self._can_enact, self._reason


class MyScalerPathBased(base.ScalerPathBased):
    cls_called: Dict[str, Any] = {}
    cls_path: str = ""

    def __init__(
        self,
        *definition: List[scaling.ScalingDefinition],
        can_enact: bool = True,
        reason: str = None,
    ) -> None:
        super().__init__(*definition)
        self._can_enact = can_enact
        self._reason = reason
        self.called = {}

    async def can_enact(self) -> Tuple[bool, str]:
        self.called[base.ScalerPathBased.can_enact.__name__] = True
        return self._can_enact, self._reason

    @classmethod
    def from_request(cls, *value: Tuple[request.ScaleRequest], **kwargs) -> "Scaler":
        cls.cls_called[base.ScalerPathBased.from_request.__name__] = value
        return MyScalerPathBased(
            *[MyScalingDefinition.from_request(val) for val in value]
        )

    @classmethod
    def _get_enact_path_value(cls, *, resource: str, field: str, target: Any) -> str:
        cls.cls_called[
            base.ScalerPathBased._get_enact_path_value.__name__
        ] = locals()
        return cls.cls_path

    @classmethod
    async def _enact_by_path_value_lst(
        cls, *, resource: str, path_value_lst: List[Tuple[str, Any]]
    ) -> None:
        cls.cls_called[
            base.ScalerPathBased._enact_by_path_value_lst.__name__
        ] = locals()


class MyCategoryType(scaling.CategoryType):
    CATEGORY_A = "Category_1"
    CATEGORY_B = "Category_2"


class MyCategoryScaleRequestParser(base.CategoryScaleRequestParser):
    cls_called = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_called = {}

    def _scaler(
        self,
        value: Iterable[scaling.ScalingDefinition],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> Iterable[base.Scaler]:
        result = MyScaler(*value)
        self.obj_called[
            base.CategoryScaleRequestParser._scaler.__name__
        ] = locals()
        return [result]

    def _to_scaling_definition(
        self,
        value: Iterable[request.ScaleRequest],
        *,
        raise_if_error: Optional[bool] = True,
    ) -> Iterable[scaling.ScalingDefinition]:
        result = [MyScalingDefinition.from_request(val) for val in value]
        self.obj_called[
            base.CategoryScaleRequestParser._to_scaling_definition.__name__
        ] = locals()
        return result

    def _filter_requests(
        self,
        value: Iterable[scaling.ScalingDefinition],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> Iterable[scaling.ScalingDefinition]:
        self.obj_called[
            base.CategoryScaleRequestParser._filter_requests.__name__
        ] = locals()
        return value

    @classmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
        cls.cls_called[
            base.CategoryScaleRequestParser.supported_categories.__name__
        ] = True
        return list(MyCategoryType)


class MyCategoryScaleRequestParserWithFilter(
    base.CategoryScaleRequestParserWithFilter
):
    cls_called = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_called = {}

    def _to_scaling_definition(
        self,
        value: Iterable[request.ScaleRequest],
        *,
        raise_if_error: Optional[bool] = True,
    ) -> Iterable[scaling.ScalingDefinition]:
        result = [MyScalingDefinition.from_request(val) for val in value]
        self.obj_called[
            base.CategoryScaleRequestParser._to_scaling_definition.__name__
        ] = locals()
        return result

    def _scaler(
        self,
        value: Iterable[scaling.ScalingDefinition],
        raise_if_invalid_request: Optional[bool] = True,
    ) -> Iterable[base.Scaler]:
        result = MyScaler(*value)
        self.obj_called[
            base.CategoryScaleRequestParser._scaler.__name__
        ] = locals()
        return [result]

    @classmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
        cls.cls_called[
            base.CategoryScaleRequestParser.supported_categories.__name__
        ] = True
        return list(MyCategoryType)


class MyCategoryScaleRequestParserWithScaler(
    base.CategoryScaleRequestParserWithScaler
):
    cls_called = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_called = {}

    def _scaling_definition_from_request(
        self,
        value: request.ScaleRequest,
    ) -> scaling.ScalingDefinition:
        result = MyScalingDefinition.from_request(value)
        self.obj_called[
            base.CategoryScaleRequestParser._to_scaling_definition.__name__
        ] = locals()
        return result

    @classmethod
    def _supported_scaling_definition_classes(
        cls,
    ) -> List[Type[scaling.ScalingDefinition]]:
        return [MyScalingDefinition]

    @classmethod
    def _scaler_class_for_definition_class(
        cls, definition_type: Type[scaling.ScalingDefinition]
    ) -> Type[base.Scaler]:
        return MyScaler

    @classmethod
    def supported_categories(cls) -> List[scaling.CategoryType]:
        cls.cls_called[
            base.CategoryScaleRequestParser.supported_categories.__name__
        ] = True
        return list(MyCategoryType)
