# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
CLI entry point to test individual parts of the code.
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

# pylint: disable=wrong-import-position
import click

from googleapiclient import errors

from yaas import logger
from yaas.cal import event_parser, google_cal
from yaas.dto import request
from yaas.gcp import cloud_run
from yaas.scaler import run, standard

# pylint: enable=wrong-import-position


_LOGGER = logger.get(__name__)


@click.group(help="CLI entry point -- Description here.")
def cli() -> None:
    """
    Click entry-point.
    """


@cli.command(help="List upcoming events")
@click.option("--cal-id", required=True, type=str, help="Which calendar ID to read")
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
) -> None:
    """
    List calendar events.

    Args:
        calendar_id: Google calendar ID
        json_creds: Google calendar JSON credentials
        start_day: From when to start listing the events
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
            scaling_targets = event_parser.to_request(event)
            print(f"Event has: {scaling_targets}")

    except errors.HttpError as error:
        print(f"An error occurred: {error}")


@cli.command(help="Set Cloud Run scaling")
@click.option(
    "--name",
    required=True,
    type=str,
    help="Cloud Run service full resource name in the form:"
    "projects/MY_PROJECT/locations/MY_LOCATION/services/MY_SERVICE",
)
@click.option(
    "--param",
    required=True,
    type=click.Choice([param.value for param in run.CloudRunCommandTypes]),
    help="Which scaling parameter to set",
)
@click.option(
    "--value", required=True, type=int, help="Value to be set to the parameter"
)
def scale_cloud_run(name: str, param: str, value: int) -> None:
    """
    Create a :py:cls:`request.ScaleRequest` and, from this request, a :py:cls:`run.CloudRunScaler`
        based on the arguments.
    It uses the scaler to enact the request.

    Args:
        name: service full-qualified name
        param: which scaling param to set
        value: value of the scaling param
    """
    req = request.ScaleRequest(
        topic=standard.StandardCategoryType.STANDARD.value,
        resource=name,
        command=f"{param} {value}",
    )
    scaler = run.CloudRunScaler.from_request(req)
    scaler.enact()


@cli.command(help="Get Cloud Run service definition")
@click.option(
    "--name",
    type=str,
    help="Cloud Run service full resource name in the form:"
    "projects/MY_PROJECT/locations/MY_LOCATION/services/MY_SERVICE",
)
def get_cloud_run(name: str) -> None:
    """
    Retrieves the service definition based on its name

    Args:
        name: service full-qualified name
    """
    result = cloud_run.get_service(name)
    print(f"Service {name} resulted in:\n{result}\n")


if __name__ == "__main__":
    cli()
