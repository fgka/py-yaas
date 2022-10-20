# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
GCP CloudFunction mandatory entry point:
* https://cloud.google.com/functions/docs/writing#functions-writing-file-structuring-python
* https://cloud.google.com/functions/docs/writing/http
* https://cloud.google.com/functions/docs/tutorials/pubsub
"""
# pylint: enable=line-too-long
from datetime import datetime
import io
import pathlib
from typing import Optional

# From: https://cloud.google.com/logging/docs/setup/python

if False:  # pylint: disable=using-constant-test
    import google.cloud.logging

    try:
        client = google.cloud.logging.Client()
        client.get_default_handler()
        client.setup_logging()
    except Exception as log_err:  # pylint: disable=broad-except
        print(f"Could not start Google Client logging. Ignoring. Error: {log_err}")

import click  # pylint: disable=wrong-import-position

from googleapiclient import errors  # pylint: disable=wrong-import-position

from yaas import logger  # pylint: disable=wrong-import-position
from yaas.cal import google_cal, parser  # pylint: disable=wrong-import-position


_LOGGER = logger.get(__name__)


@click.group(help="CLI entry point -- Description here.")
def cli() -> None:
    """
    Click entry-point
    :return:
    """


@cli.command(help="List upcoming events")
@click.option("--cal-id", required=True, type=str, help="Which cal to read.")
@click.option(
    "--json-creds", required=False, type=click.File("r"), help="JSON credentials file"
)
@click.option(
    "--start-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31"
)
def list_events(
    calendar_id: str,
    json_creds: Optional[io.TextIOWrapper] = None,
    start_day: Optional[str] = None,
):
    """
    List cal events.

    Args:
        calendar_id:
        json_creds:
        start_day:

    Returns:

    """
    try:
        credentials_json = None
        if json_creds:
            credentials_json = pathlib.Path(json_creds.name).absolute()
        if start_day:
            start = datetime.fromisoformat(start_day)
        events = google_cal.list_upcoming_events(
            calendar_id=calendar_id, credentials_json=credentials_json, start=start
        )

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            scaling_targets = parser.to_scaling(event)
            print(f"Event has: {scaling_targets}")

    except errors.HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    cli()
