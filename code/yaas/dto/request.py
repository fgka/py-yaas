# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
from collections import abc
from typing import Iterable, List, Optional

import attrs

from yaas.dto import dto_defaults
from yaas import const


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


@attrs.define(**const.ATTRS_DEFAULTS)
class ScaleRequestCollection(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Intended to be used to aggregate multiple :py:class:`ScaleRequest` through PubSub.
    Instead of instantiating it directly, use the factory method to clean it up.
    """

    collection: List[ScaleRequest] = attrs.field(
        validator=attrs.validators.deep_iterable(
            member_validator=attrs.validators.instance_of(ScaleRequest)
        )
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
