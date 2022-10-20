# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Default values for creating an attributes class. To be used as::

    import attrs

    @attrs.define(**attrs_defaults.ATTRS_DEFAULTS)
    class MyAttrs: pass
"""
import re
from typing import Dict


###########
#  ATTRS  #
###########

ATTRS_DEFAULTS: Dict[str, bool] = dict(
    kw_only=True,
    str=True,
    repr=True,
    eq=True,
    hash=True,
    frozen=True,
    slots=True,
)

####################
#  Scaling Target  #
####################

REQUEST_PATH_SEP: str = "."

# CloudRun
CLOUD_RUN_NAME_REGEX: re.Pattern = re.compile(
    "^projects/([^/]+)/locations/([^/]+)/services/([^/]+)$"
)
CLOUD_RUN_UPDATE_REQUEST_SCALING_TARGET_PARAM: str = REQUEST_PATH_SEP.join(
    ["service", "template", "scaling", "min_instance_count"]
)
# pylint: disable=line-too-long
"""
It corresponds to the _path_ in the API:
    `UpdateServiceRequest`_.`Service`_.`RevisionTemplate`_.`RevisionScaling`_

.. _UpdateServiceRequest: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.UpdateServiceRequest
.. _Service: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.Service
.. _RevisionTemplate: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionTemplate
.. _RevisionScaling: https://cloud.google.com/python/docs/reference/run/latest/google.cloud.run_v2.types.RevisionScaling
"""
# pylint: enable=line-too-long
CLOUD_RUN_UPDATE_REQUEST_NAME_PATH: str = REQUEST_PATH_SEP.join(["service", "name"])
