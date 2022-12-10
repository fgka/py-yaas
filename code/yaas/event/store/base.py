# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Basic definition of types and expected functionality for resource scaler.
"""
import abc
from typing import Any, List, Tuple

import attrs

from yaas.dto import dto_defaults, request
from yaas import const, logger

_LOGGER = logger.get(__name__)



class Sna(abc.ABC):
    """
    Generic class to define a scaler.
    """

    def __init__(self, definition: ScalingDefinition) -> None:
        if not isinstance(definition, ScalingDefinition):
            raise TypeError(
                f"The argument definition must be of type {ScalingDefinition.__name__}"
            )
        self._definition = definition
        super().__init__()
