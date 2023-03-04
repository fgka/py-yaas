# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Default values for creating an attributes class. To be used as::

import attrs

@attrs.define(**attrs_defaults.ATTRS_DEFAULTS)
class MyAttrs: pass
"""
from typing import Dict

############
#  Common  #
############

ENCODING_UTF8: str = "UTF-8"


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

#############
#  Command  #
#############

CMD_TYPE_UPDATE_CALENDAR_CREDENTIALS_SECRET = "UPDATE_CALENDAR_CREDENTIALS_SECRET"
CMD_TYPE_UPDATE_CALENDAR_CACHE = "UPDATE_CALENDAR_CACHE"
CMD_TYPE_SEND_SCALING_REQUESTS = "SEND_SCALING_REQUESTS"
