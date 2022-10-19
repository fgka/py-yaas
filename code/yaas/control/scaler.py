# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Source: https://developers.google.com/calendar/api/quickstart/python
Source: https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/
"""
# pylint: enable=line-too-long

from yaas.calendar import scaling_target


def apply(value: scaling_target.BaseScalingTarget) -> None:
    """

    Args:
        value:

    Returns:

    """
    # validate
    if not isinstance(value, scaling_target.BaseScalingTarget):
        raise TypeError(f"Invalid input <{value}>({type(value)}")
    # apply scaling
    match value.type:
        case scaling_target.ScalingTargetType.CLOUD_RUN:
            _apply_cloud_run(value)
        case _:
            raise ValueError(f"Scaling target of type {value.type} is not supported. Full request: {value}")


def _apply_cloud_run(value: scaling_target.CloudRunScalingTarget) -> None:
    """

    Args:
        value:

    Returns:

    """
    pass