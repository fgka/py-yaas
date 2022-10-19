# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Default values for creating an attributes class. To be used as::

    import attrs

    @attrs.define(**attrs_defaults.ATTRS_DEFAULTS)
    class MyAttrs: pass
"""

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
