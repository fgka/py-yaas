# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=missing-function-docstring,assignment-from-no-return,c-extension-no-member
# pylint: disable=protected-access,redefined-outer-name,using-constant-test,redefined-builtin
# pylint: disable=invalid-name,attribute-defined-outside-init,too-few-public-methods
# type: ignore
import base64
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import flask

from yaas_common import const
from yaas_common import request
from yaas_gcp import pubsub
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


##########
# PubSub #
##########


class _MyRequest(flask.Request):
    def __init__(  # pylint: disable=super-init-not-called
        self, json_payload: Optional[Any] = None
    ):
        self.called = {}
        self._json_payload = json_payload

    def get_json(self) -> str:  # pylint: disable=arguments-differ
        self.called[_MyRequest.get_json.__name__] = True
        return self._json_payload

    def __repr__(self) -> str:
        return _MyRequest.__name__


_TEST_ISO_DATE_STR_PREFIX: str = "2022-01-31T11:01:38"


def create_event(
    obj_dict: Dict[str, Any],
    as_request: bool,
    publish_date_str: Optional[str] = _TEST_ISO_DATE_STR_PREFIX,
):
    data = create_event_str(obj_dict, as_bytes=not as_request)
    if as_request:
        payload = {
            pubsub._EVENT_MESSAGE_KEY: {
                pubsub._EVENT_MESSAGE_DATA_KEY: data,
                pubsub._MESSAGE_PUBLISH_TIME_KEY: publish_date_str,
            }
        }
        result = _MyRequest(payload)
    else:
        result = {pubsub._EVENT_MESSAGE_DATA_KEY: data}
    return result


def create_event_str(data: Any, as_bytes: Optional[bool] = True) -> Union[str, bytes]:
    result = base64.b64encode(bytes(json.dumps(data).encode(const.ENCODING_UTF8)))
    if not as_bytes:
        result = result.decode(encoding=const.ENCODING_UTF8)
    return result
