# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
from collections import abc
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Union, Tuple

import attrs

from yaas.dto import dto_defaults
from yaas import const


@attrs.define(**const.ATTRS_DEFAULTS)
class Range(dto_defaults.HasFromJsonString):  # pylint: disable=too-few-public-methods
    """
    Defines a range of time.
    """

    period_minutes: int = attrs.field(validator=attrs.validators.gt(0))
    now_diff_minutes: int = attrs.field(validator=attrs.validators.instance_of(int))

    def timestamp_range(self) -> Tuple[int, int]:
        """
        Will compute the range based on now for start.

        Returns:

        """
        start_utc = datetime.utcnow() + timedelta(minutes=self.now_diff_minutes)
        end_utc = start_utc + timedelta(minutes=self.period_minutes)
        return start_utc.timestamp(), end_utc.timestamp()

    def as_log_str(self) -> str:
        """
        A nicer way to log an object.
        """
        start_utc, end_utc = self.timestamp_range()
        start_dt = datetime.fromtimestamp(start_utc)
        end_dt = datetime.fromtimestamp(end_utc)
        delta = end_dt - start_dt
        return f"{self} = [{start_dt}, {end_dt}] ~ {delta}"


@attrs.define(**const.ATTRS_DEFAULTS)
class ScaleRequest(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    To be sent as a scale request to a particular topic.
    """

    topic: str = attrs.field(validator=attrs.validators.instance_of(str))
    resource: str = attrs.field(validator=attrs.validators.instance_of(str))
    command: str = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
    timestamp_utc: int = attrs.field(
        default=None,
        validator=attrs.validators.optional(
            attrs.validators.and_(
                attrs.validators.instance_of(int),
                attrs.validators.gt(0),
            )
        ),
    )
    original_json_event: str = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )


def _convert_list_dict(
    value: List[Union[ScaleRequest, Dict[str, Any]]]
) -> List[ScaleRequest]:
    """
    To be used when converting back from full dictionary.
    """
    # validate input
    if not isinstance(value, abc.Iterable):
        raise TypeError(
            f"Argument is not {Iterable.__name__}. Got: <{value}>({type(value)})"
        )
    # convert
    result = []
    for ndx, val in enumerate(value):
        if isinstance(val, ScaleRequest):
            result.append(val)
        else:
            try:
                obj = ScaleRequest.from_dict(val)
            except Exception as err:
                raise ValueError(
                    f"Could not convert item <{val}>[{ndx}]({type(val)}) to {ScaleRequest.__name__}. Error: {err}. Values: {value}"
                ) from err
            result.append(obj)
    return result


@attrs.define(**const.ATTRS_DEFAULTS)
class ScaleRequestCollection(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Intended to be used to aggregate multiple :py:class:`ScaleRequest` through PubSub.
    Instead of instantiating it directly, use the factory method to clean it up.
    """

    collection: List[ScaleRequest] = attrs.field(
        converter=_convert_list_dict,
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(ScaleRequest)
        ),
    )

    @classmethod
    def from_lst(
        cls,
        value: Iterable[ScaleRequest],
        remove_original_json_event: Optional[bool] = True,
    ) -> "ScaleRequestCollection":
        """
        Will clean up, optionally, the ``original_json_event``.
        This might be relevant to improve privacy when sent to an external topic,
            imagine that the request has extra text not relevant for the scaling request.
        Args:
            value:
                Values to use to create the collection.
            remove_original_json_event:
                If set to :py:obj:`True` will create a new instance of :py:class:`ScaleRequest`
                for each value without the ``original_json_event`` field.

        Returns:

        """
        # validate input
        if not isinstance(value, abc.Iterable):
            raise TypeError(
                f"The value must be an instance of {abc.Iterable.__name__}. "
                f"Got: <{value}>({type(value)})"
            )
        # logic
        collection = []
        for ndx, val in enumerate(value):
            if not isinstance(val, ScaleRequest):
                raise TypeError(
                    f"Value <{val}>({type(val)})[{ndx}] is not a {ScaleRequest.__name__}. "
                    f"All values: {value}"
                )
            if remove_original_json_event:
                val = val.clone(original_json_event=None)
            collection.append(val)
        return ScaleRequestCollection(collection=collection)
