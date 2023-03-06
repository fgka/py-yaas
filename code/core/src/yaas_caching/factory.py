# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Creates the proper py:class:`base.StoreContextManager` instance."""
from yaas_caching import base, file, gcs
from yaas_common import logger
from yaas_config import config

_LOGGER = logger.get(__name__)


def store_from_cache_config(value: config.CacheConfig) -> base.StoreContextManager:
    """Based on the configuration will create the proper py:class:`base.StoreContextManager` instance.

    Args:
        value:

    Returns:

    """
    # validate input
    if not isinstance(value, config.CacheConfig):
        raise TypeError(f"Argument must be an instance of {config.CacheConfig.__name__}. Got: <{value}>({type(value)})")
    # logic
    if value.type == config.CacheType.LOCAL_JSON_LINE.value:
        result = file.JsonLineFileStoreContextManager(
            json_line_file=value.json_line_file,
            archive_json_line_file=value.archive_json_line_file,
        )
    elif value.type == config.CacheType.LOCAL_SQLITE.value:
        result = file.SQLiteStoreContextManager(sqlite_file=value.sqlite_file)
    elif value.type == config.CacheType.GCS_SQLITE.value:
        result = gcs.GcsObjectStoreContextManager(
            bucket_name=value.bucket_name,
            db_object_path=value.object_path,
        )
    else:
        raise ValueError(
            f"Configuration of type {value.type} is not supported. "
            f"Check implementation of {store_from_cache_config.__name__} in {__file__}"
        )
    return result
