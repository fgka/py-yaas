# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Default values related to Cloud Run.
"""
from yaas import xpath


###########################
#  Update Request: paths  #
###########################

CLOUD_SQL_STATE_KEY: str = "state"
CLOUD_SQL_STATE_OK: str = "RUNNABLE"

# min_instance_count
CLOUD_SQL_SERVICE_SCALING_INSTANCE_TYPE_PARAM: str = xpath.REQUEST_PATH_SEP.join(
    ["settings", "tier"]
)
# pylint: disable=line-too-long
"""
It corresponds to the _path_ in the API:
    `DatabaseInstance`_.`Settings`_.tier

.. _DatabaseInstance: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#DatabaseInstance
.. _Settings: https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1beta4/instances#Settings
"""
# pylint: enable=line-too-long
