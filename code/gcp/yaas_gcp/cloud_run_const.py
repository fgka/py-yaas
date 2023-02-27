# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Default values related to Cloud Run.
"""
from typing import List

from yaas_common import xpath


###################
#  Resource name  #
###################

CLOUD_RUN_NAME_TOKENS: List[str] = ["projects", "locations", "services"]

###########################
#  Update Request: paths  #
###########################


# min_instance_count
CLOUD_RUN_SERVICE_SCALING_MIN_INSTANCES_PARAM: str = xpath.REQUEST_PATH_SEP.join(
    ["template", "scaling", "min_instance_count"]
)
# pylint: disable=line-too-long
"""
It corresponds to the _path_ in the API:
    `Service`_.`RevisionTemplate`_.`RevisionScaling`_

.. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
.. _RevisionTemplate: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionTemplate
.. _RevisionScaling: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionScaling
"""
# pylint: enable=line-too-long

# max_instance_count
CLOUD_RUN_SERVICE_SCALING_MAX_INSTANCES_PARAM: str = xpath.REQUEST_PATH_SEP.join(
    ["template", "scaling", "max_instance_count"]
)
# pylint: disable=line-too-long
"""
It corresponds to the _path_ in the API:
    `Service`_.`RevisionTemplate`_.`RevisionScaling`_

.. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
.. _RevisionTemplate: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionTemplate
.. _RevisionScaling: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionScaling
"""
# pylint: enable=line-too-long

# max_instance_request_concurrency
CLOUD_RUN_SERVICE_SCALING_CONCURRENCY_PARAM: str = xpath.REQUEST_PATH_SEP.join(
    ["template", "max_instance_request_concurrency"]
)
# pylint: disable=line-too-long
"""
It corresponds to the _path_ in the API:
    `Service`_.`RevisionTemplate`_

.. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
.. _RevisionTemplate: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionTemplate
"""

############################
#  Update Request: ignore  #
############################

# pylint: enable=line-too-long
CLOUD_RUN_UPDATE_REQUEST_SERVICE_PATHS_TO_REMOVE: List[str] = [
    "etag",
    "create_time",
    "creator",
    "delete_time",
    "generation",
    "last_modifier",
    "latest_created_revision",
    "latest_ready_revision",
    "launch_stage",
    "observed_generation",
    "traffic",
    "traffic_statuses",
    "uid",
    "update_time",
]

##############################
#  Update Request: revision  #
##############################

CLOUD_RUN_SERVICE_REVISION_PATH: str = xpath.REQUEST_PATH_SEP.join(
    ["template", "revision"]
)
