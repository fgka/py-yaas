# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""Cloud Run service for scaling resources."""
from typing import Any, Dict, List, Optional, Tuple, Union

import flask
from yaas_command import pubsub_dispatcher
from yaas_common import logger
from yaas_scaler import base

_LOGGER = logger.get(__name__)


async def enact_requests(
    *,
    parser: base.CategoryScaleRequestParser,
    pubsub_event: Union[flask.Request, Dict[str, Any]],
    iso_str_timestamp: Optional[str] = None,
) -> None:
    """
    Given the input event, will extract all requests and enact them.
    Args:
        parser:
        pubsub_event:
        iso_str_timestamp:

    Returns:

    """
    _LOGGER.debug("Starting %s with %s", enact_requests.__name__, locals())
    # validate input
    if not isinstance(parser, base.CategoryScaleRequestParser):
        raise TypeError(
            f"Parser must be an instance of {base.CategoryScaleRequestParser.__name__}. "
            f"Got: <{parser}>({type(parser)})"
        )
    # logic
    req_lst = pubsub_dispatcher.from_event(event=pubsub_event, iso_str_timestamp=iso_str_timestamp)
    if not isinstance(req_lst, list):
        raise TypeError(
            f"Expecting a list of requests from event. Got: <{req_lst}>({type(req_lst)}). Event: {pubsub_event}"
        )
    result: List[Tuple[bool, base.Scaler]] = await parser.enact(*req_lst, singulate_if_only_one=False)
    for success_scaler in result:
        success, scaler = success_scaler
        if not success:
            _LOGGER.error("Could not enact request <%s>. Check logs", scaler.definitions)
