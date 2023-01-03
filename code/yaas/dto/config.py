# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Configurations.
"""
from typing import Any, Callable, Dict, Optional

import attrs

from yaas.dto import dto_defaults
from yaas import const


class CacheType(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    Supported caching.
    """

    LOCAL_JSON_LINE = "local_json"
    LOCAL_SQLITE = "local_sqlite"
    GCS_SQLITE = "gcs_sqlite"

    @classmethod
    def default(cls) -> Any:
        """
        Default caching type.
        """
        return CacheType.GCS_SQLITE


@attrs.define(**const.ATTRS_DEFAULTS)
class CacheConfig(  # pylint: disable=too-few-public-methods
    dto_defaults.HasFromJsonString
):
    """
    Common class to extend to define cache destination.
    """

    type: str = attrs.field(validator=attrs.validators.instance_of(str))

    @type.validator
    def _is_type_valid(self, attribute: attrs.Attribute, value: str):
        if not CacheType.from_str(value):
            raise ValueError(
                f"Attribute {attribute.name} does not accept <{value}>. "
                f"Valid values are: {list(CacheType)}"
            )
        self._is_type_valid_subclass(attribute.name, value)

    def _is_type_valid_subclass(self, name: str, value: str):
        pass

    @classmethod
    def from_json(cls, json_string: str, context: Optional[str] = None) -> Any:
        """
        Act as factory.
        Args:
            json_string:
            context:

        Returns:

        """
        from_json_cls_method = dto_defaults.HasFromJsonString.from_json.__func__
        return cls._factory(from_json_cls_method, json_string, context)

    @classmethod
    def _factory(cls, factory_fn: Callable, *args, **kwargs) -> Any:
        # get the type
        base_cfg = factory_fn(CacheConfig, *args, **kwargs)
        # factory logic
        if base_cfg.type == CacheType.GCS_SQLITE.value:
            result = factory_fn(GcsCacheConfig, *args, **kwargs)
        elif base_cfg.type == CacheType.LOCAL_JSON_LINE.value:
            result = factory_fn(LocalJsonLineCacheConfig, *args, **kwargs)
        elif base_cfg.type == CacheType.LOCAL_SQLITE.value:
            result = factory_fn(LocalSqliteCacheConfig, *args, **kwargs)
        else:
            raise TypeError(
                f"Cache type <{base_cfg.type}> is not a supported type. "
                f"Check implementation of {factory_fn.__name__} in {cls.__name__}. "
                f"Args: <{args}>. "
                f"Kwargs: <{kwargs}>"
            )
        return result

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> Any:
        """
        Required to work as factory as well for cascading effect.
        Args:
            value:

        Returns:

        """
        from_dict_cls_method = dto_defaults.HasFromJsonString.from_dict.__func__
        return cls._factory(from_dict_cls_method, value)


@attrs.define(**const.ATTRS_DEFAULTS)
class LocalJsonLineCacheConfig(CacheConfig):  # pylint: disable=too-few-public-methods
    """
    Storing as JSON line files locally.

    **NOTE**: use for test only.
    """

    json_line_file: str = attrs.field(validator=attrs.validators.instance_of(str))
    archive_json_line_file: str = attrs.field(
        validator=attrs.validators.instance_of(str)
    )

    def _is_type_valid_subclass(self, name: str, value: str):
        valid_type = CacheType.LOCAL_JSON_LINE
        if CacheType.from_str(value) != valid_type:
            raise ValueError(f"Value for field {name} must be {valid_type}")


@attrs.define(**const.ATTRS_DEFAULTS)
class LocalSqliteCacheConfig(CacheConfig):  # pylint: disable=too-few-public-methods
    """
    Storing as a local SQLite DB file.

    **NOTE**: use for test only.
    """

    sqlite_file: str = attrs.field(validator=attrs.validators.instance_of(str))

    def _is_type_valid_subclass(self, name: str, value: str):
        valid_type = CacheType.LOCAL_SQLITE
        if CacheType.from_str(value) != valid_type:
            raise ValueError(f"Value for field {name} must be {valid_type}")


_DEFAULT_GCS_CACHE_OBJECT_PATH: str = "cache/event_cache.db"


@attrs.define(**const.ATTRS_DEFAULTS)
class GcsCacheConfig(CacheConfig):  # pylint: disable=too-few-public-methods
    """
    Defines GCS location for the cache.
    """

    bucket_name: str = attrs.field(validator=attrs.validators.instance_of(str))
    object_path: str = attrs.field(
        default=_DEFAULT_GCS_CACHE_OBJECT_PATH,
        validator=attrs.validators.instance_of(str),
    )

    def _is_type_valid_subclass(self, name: str, value: str):
        valid_type = CacheType.GCS_SQLITE
        if CacheType.from_str(value) != valid_type:
            raise ValueError(f"Value for field {name} must be {valid_type}")


@attrs.define(**const.ATTRS_DEFAULTS)
class Config(dto_defaults.HasFromJsonString):  # pylint: disable=too-few-public-methods
    """
    Configuration to say to which PubSub topic each YAAS topic goes.
    """

    calendar_id: str = attrs.field(validator=attrs.validators.instance_of(str))
    calendar_secret_name: str = attrs.field(validator=attrs.validators.instance_of(str))
    cache_config: CacheConfig = attrs.field(
        validator=attrs.validators.instance_of(CacheConfig)
    )
    topic_to_pubsub: Dict[str, str] = attrs.field(
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.instance_of(str),
            value_validator=attrs.validators.instance_of(str),
        )
    )
