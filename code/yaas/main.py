# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP CloudFunction mandatory entry point:
* https://cloud.google.com/functions/docs/writing#functions-writing-file-structuring-python
* https://cloud.google.com/functions/docs/writing/http
* https://cloud.google.com/functions/docs/tutorials/pubsub
"""
# pylint: enable=line-too-long
from typing import Optional

# From: https://cloud.google.com/logging/docs/setup/python
import google.cloud.logging

try:
    client = google.cloud.logging.Client()
    client.get_default_handler()
    client.setup_logging()
except Exception as log_err:  # pylint: disable=broad-except
    print(f"Could not start Google Client logging. Ignoring. Error: {log_err}")

import click  # pylint: disable=wrong-import-position

from yaas import logger  # pylint: disable=wrong-import-position


_LOGGER = logger.get(__name__)


@click.group(help="CLI entry point -- Description here.")
def cli() -> None:
    """
    Click entry-point
    :return:
    """


@cli.command(help="A command")
@click.option("--arg-a-long", "-a", required=True, type=str, help="Mandatory argument")
@click.option(
    "--arg-b-long",
    "-b",
    default="",
    required=False,
    type=str,
    help="An optional argument.",
)
def some_cmd(arg_a_long: str, arg_b_long: Optional[str] = None) -> None:
    """
    A command with 2 arguments
    Args:
        arg_a_long:
        arg_b_long:

    Returns:

    """
    _LOGGER.info("Arguments: %s", locals())
    print(
        f"Arguments: <{arg_a_long}>({type(arg_a_long)}) and <{arg_b_long}>({type(arg_b_long)})"
    )


if __name__ == "__main__":
    cli()
