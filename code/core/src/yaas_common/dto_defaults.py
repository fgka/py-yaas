# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Basic classes to use to create DTOs using `attrs`_.

.. attrs: https://www.attrs.org/en/stable/
"""
import enum
import json
from typing import Any, Dict, Optional

import attrs

from yaas_common import logger

_LOGGER = logger.get(__name__)


class HasIsEmpty:  # pylint: disable=too-few-public-methods
    """To add :py:meth:`is_empty` to children."""

    def is_empty(self) -> bool:
        """Check all fields and returns :py:obj:`True` if they are all
        :py:obj:`None`.

        Returns:
        """
        # pylint: disable=use-a-generator
        return all([val is None for val in attrs.asdict(self).values()])


class HasPatchWith(HasIsEmpty):
    """To add :py:meth:`return_value_if_empty` to children."""

    def patch_is_substitution(self) -> bool:
        """Controls how :py:meth:`patch_with` works. If it is complete
        substitution or a merge.

        Returns:
        """
        return True

    def patch_with(self, value: Any) -> Any:
        """The behavior depends on :py:meth:`patch_is_substitution`. The
        argument `value` is only considered if it is of the same type as
        current instance.

        If :py:meth:`patch_is_substitution` is :py:obj:`True` will return only return `value`
        if the current instance is empty, i.e., :py:meth:`is_empty` returns :py:obj:`True`.

        If :py:meth:`patch_is_substitution` is :py:obj:`False`,
        will check each attribute individually and apply :py:meth:`patch_with` if applicable.

        **NOTE**: It never changes the involved objects.
        If the merge strategy is chosen, will create a new object with merge result.

        Args:
            value:

        Returns:
        """
        result = self
        if self.patch_is_substitution():
            # substitution
            if self.is_empty() and isinstance(value, self.__class__):
                result = value
        elif isinstance(value, self.__class__):
            result = self._merge(value)
        return result

    def _merge(self, value: Any) -> Any:
        try:
            kwargs = self._create_merge_kwargs(value)
        except Exception as err:
            raise ValueError(
                "Could not create merge kwargs."
                f" Current object: <{self}> ({self.__class__.__name__})."
                f" Value: <{value}>."
                f" Error: {err}"
            ) from err
        try:
            result = self.__class__(**kwargs)
        except Exception as err:
            raise ValueError(
                f"Could not instantiate <{self.__class__.__name__}>" f" from kwargs <{kwargs}>." f" Error: {err}"
            ) from err
        return result

    def _create_merge_kwargs(self, value: Any) -> Dict[str, Any]:
        result = {}
        for field in list(attrs.fields(self.__class__)):
            try:
                result_field = self._create_field_value(field, value)
                result[field.name] = result_field
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Could not retrieve field <%s> from <%s> for type <%s>. Ignoring. Error: <%s>",
                    field.name,
                    value,
                    self.__class__.__name__,
                    err,
                )
        return result

    def _create_field_value(self, field: attrs.Attribute, value: Any) -> Any:
        self_field = getattr(self, field.name)
        value_field = getattr(value, field.name)
        result = self_field
        if self_field is None:
            # clear substitution
            result = value_field
        elif self_field is not None and value_field is not None and issubclass(field.type, HasPatchWith):
            # recursion on patch_with()
            try:
                result = self_field.patch_with(value_field)
            except Exception as err:  # pylint: disable=broad-except
                value_field = None
                _LOGGER.warning(
                    "Could create field <%s> patching <%s> with <%s> for type <%s>. Ignoring. Error: %s",
                    field.name,
                    self_field,
                    value_field,
                    self.__class__.__name__,
                    err,
                )
        return result


class HasFromDict(HasPatchWith):
    """To add :py:meth:`from_dict` to children."""

    def as_dict(self) -> Dict[str, str]:
        """Simple wrapper for:: attrs.asdict(self)

        Returns:
        """
        return attrs.asdict(self)

    def clone(self, **overwrite) -> Any:
        """Will create a new instance of the same type and apply overwrites, if
        given.

        Args:
            overwrite:

        Returns:
        """
        kwargs = self.as_dict()
        if isinstance(overwrite, dict):
            for key, val in overwrite.items():
                if key in kwargs:
                    kwargs[key] = val
        return self.__class__.from_dict(kwargs)

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> Any:
        """Converts a simple :py:class:`dict` into a instance of the current
        class.

        Args:
            value:

        Returns:
        """
        kwargs = {}
        if isinstance(value, dict):
            try:
                kwargs = cls._create_kwargs(value)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Could not parse %s from dictionary <%s>. Error: %s",
                    cls.__name__,
                    value,
                    err,
                )
        try:
            result = cls(**kwargs)
        except Exception as err:
            raise ValueError(f"Could not instantiate <{cls.__name__}> from kwargs <{kwargs}>. Error: {err}") from err
        return result

    @classmethod
    def _create_kwargs(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        """Because of how :py:module:`attrs` works, the `value` must be trimmed
        to the exact attributes available to be used as `kwargs`.

        **NOTE**: It a field is of type :py:class:`HasFromDict`
                  it will call :py:meth:`from_dict` recursively.

        Args:
            value:

        Returns:
        """
        result = {}
        for field in list(attrs.fields(cls)):
            field_value = value.get(field.name)
            if (
                field_value is not None
                and isinstance(field.type, type)  # things like lists and dicts are of type: typing.List/typing.Dict
                and issubclass(field.type, HasFromDict)
            ):
                # recursion on from_dict()
                try:
                    field_value = field.type.from_dict(field_value)
                except Exception as err:  # pylint: disable=broad-except
                    field_value = None
                    _LOGGER.warning(
                        "Could create field <%s> from dict for type <%s>. Ignoring. Error: %s",
                        field.name,
                        cls.__name__,
                        err,
                    )
            result[field.name] = field_value
        return result


class HasFromJsonString(HasFromDict):
    """To add :py:meth:`from_json` to children."""

    @classmethod
    def from_json(cls, json_string: str, context: Optional[str] = None) -> Any:
        """Will parse `json_string` and use :py:meth:`from_dict` to get the
        instance.

        Args:
            json_string:
            context:

        Returns:
        """
        value = {}
        try:
            value = json.loads(json_string)
        except Exception as err:  # pylint: disable=broad-except
            error_context = ""
            if context:
                error_context = f". Context: {context}"
            _LOGGER.warning(
                "Could not parse JSON string <%s> for type <%s>%s. Ignoring. Error: %s",
                json_string,
                cls.__name__,
                error_context,
                err,
            )
        return cls.from_dict(value)

    def as_json(self) -> str:
        """Converts the current object into a JSON string.

        Returns:
        """
        # first to dict
        try:
            value_dict = attrs.asdict(self)
        except Exception as err:
            raise ValueError(
                f"Could not convert <{self}> to a dictionary for type {self.__class__.__name__}." f" Error: {err}"
            ) from err
        # now to a JSON string from the dict
        try:
            result = json.dumps(value_dict)
        except Exception as err:
            raise ValueError(
                f"Could not convert <{value_dict}>, from <{self}>, to a JSON string. Error: {err}"
            ) from err
        return result


class EnumWithFromStrIgnoreCase(enum.Enum):
    """To add :py:meth:`from_str` to children."""

    @classmethod
    def from_str(cls, value: str) -> Any:
        """Parses a string value into corresponding :py:class:`enum.Enum`
        comparing it with the values and ignoring case.

        Args:
            value:

        Returns:
        """
        result = None
        if value is not None:
            for val in cls:
                if val.value.lower() == value.lower().strip():
                    result = val
                    break
        return result

    def name_equal_str(self, value: str) -> bool:
        """
        If the argument ``value`` is a string representation of the current *name*, ignoring case,
        returns :py:obj:`True`.
        Example::
            class MyEnum(EnumWithFromStrIgnoreCase):
                ITEM = "Item_1"

            assert MyEnum.ITEM.name_equal_str("ITEM")
            assert MyEnum.ITEM.name_equal_str("item")
            assert MyEnum.ITEM.name_equal_str("Item")
            assert not MyEnum.ITEM.name_equal_str("Item_1")

        Args:
            value:

        Returns:
        """
        result = False
        if isinstance(value, str):
            result = self.name.lower() == value.lower().strip()
        return result
