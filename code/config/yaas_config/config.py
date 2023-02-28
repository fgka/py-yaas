# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Configurations.
"""
from typing import Any, Callable, Dict, Optional

import attrs

from yaas_common import const, dto_defaults
from yaas_gcp import gcs


class CacheType(dto_defaults.EnumWithFromStrIgnoreCase):
    """
    Supported caching.
    """

    CALENDAR = "calendar"
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
    def _is_type_valid(self, attribute: attrs.Attribute, value: str) -> None:
        if not CacheType.from_str(value):
            raise ValueError(
                f"Attribute {attribute.name} does not accept <{value}>. "
                f"Valid values are: {list(CacheType)}"
            )
        self._is_type_valid_subclass(attribute.name, value)

    def _is_type_valid_subclass(self, name: str, value: str) -> None:
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
        try:
            result = cls._factory(from_json_cls_method, json_string, context)
        except Exception as err:
            raise ValueError(
                f"Could not parse content into {cls.__name__}. Content: {json_string}"
            ) from err
        return result

    @classmethod
    def _factory(cls, factory_fn: Callable, *args, **kwargs) -> Any:
        # get the type
        base_cfg = factory_fn(CacheConfig, *args, **kwargs)
        # factory logic
        if base_cfg.type == CacheType.CALENDAR.value:
            result = factory_fn(CalendarCacheConfig, *args, **kwargs)
        elif base_cfg.type == CacheType.GCS_SQLITE.value:
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
class CalendarCacheConfig(CacheConfig):  # pylint: disable=too-few-public-methods
    """
    Calendar configurations.
    """

    calendar_id: str = attrs.field(validator=attrs.validators.instance_of(str))
    secret_name: str = attrs.field(validator=attrs.validators.instance_of(str))

    def _is_type_valid_subclass(self, name: str, value: str) -> None:
        valid_type = CacheType.CALENDAR
        if CacheType.from_str(value) != valid_type:
            raise ValueError(f"Value for field {name} must be {valid_type}")


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

    def _is_type_valid_subclass(self, name: str, value: str) -> None:
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

    def _is_type_valid_subclass(self, name: str, value: str) -> None:
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

    def _is_type_valid_subclass(self, name: str, value: str) -> None:
        valid_type = CacheType.GCS_SQLITE
        if CacheType.from_str(value) != valid_type:
            raise ValueError(f"Value for field {name} must be {valid_type}")


MINIMUM_EXPIRED_ENTRIES_MAX_RETENTION_BEFORE_ARCHIVE_IN_DAYS: int = 1
DEFAULT_EXPIRED_ENTRIES_MAX_RETENTION_BEFORE_ARCHIVE_IN_DAYS: int = (
    MINIMUM_EXPIRED_ENTRIES_MAX_RETENTION_BEFORE_ARCHIVE_IN_DAYS
)
MINIMUM_ARCHIVE_MAX_RETENTION_BEFORE_REMOVAL_IN_DAYS: int = 30
DEFAULT_ARCHIVE_MAX_RETENTION_BEFORE_REMOVAL_IN_DAYS: int = 365


@attrs.define(**const.ATTRS_DEFAULTS)
class DataRetentionConfig(
    dto_defaults.HasFromJsonString
):  # pylint: disable=too-few-public-methods
    """
    Specify the different ways data is archived and removed.
    """

    expired_entries_max_retention_before_archive_in_days: int = attrs.field(
        default=DEFAULT_EXPIRED_ENTRIES_MAX_RETENTION_BEFORE_ARCHIVE_IN_DAYS,
        validator=attrs.validators.and_(
            attrs.validators.instance_of(int),
            attrs.validators.ge(
                MINIMUM_EXPIRED_ENTRIES_MAX_RETENTION_BEFORE_ARCHIVE_IN_DAYS
            ),
        ),
    )
    max_retention_archive_before_removal_in_days: int = attrs.field(
        default=DEFAULT_ARCHIVE_MAX_RETENTION_BEFORE_REMOVAL_IN_DAYS,
        validator=attrs.validators.and_(
            attrs.validators.instance_of(int),
            attrs.validators.ge(MINIMUM_ARCHIVE_MAX_RETENTION_BEFORE_REMOVAL_IN_DAYS),
        ),
    )


@attrs.define(**const.ATTRS_DEFAULTS)
class Config(dto_defaults.HasFromJsonString):  # pylint: disable=too-few-public-methods
    """
    Configuration to say to which PubSub topic each YAAS topic goes.
    """

    calendar_config: CalendarCacheConfig = attrs.field(
        validator=attrs.validators.instance_of(CalendarCacheConfig)
    )
    cache_config: CacheConfig = attrs.field(
        validator=attrs.validators.instance_of(CacheConfig)
    )
    topic_to_pubsub: Dict[str, str] = attrs.field(
        validator=attrs.validators.deep_mapping(
            key_validator=attrs.validators.instance_of(str),
            value_validator=attrs.validators.instance_of(str),
        )
    )
    topic_to_pubsub_gcs: str = attrs.field(
        default=None,
        validator=attrs.validators.optional(attrs.validators.instance_of(str)),
    )
    retention_config: DataRetentionConfig = attrs.field(
        default=None,
        converter=attrs.converters.default_if_none(
            default=attrs.Factory(DataRetentionConfig)
        ),
        validator=attrs.validators.instance_of(DataRetentionConfig),
    )

    @topic_to_pubsub_gcs.validator
    def _is_topic_to_pubsub_gcs_valid(
        self, attribute: attrs.Attribute, value: Optional[str]
    ) -> None:
        if value is not None:
            if not isinstance(value, str):
                raise TypeError(
                    f"Value for {attribute.name} can be None or a string. "
                    f"Got: <{value}>({type(value)})"
                )
            gcs.get_bucket_and_prefix_from_uri(value)
