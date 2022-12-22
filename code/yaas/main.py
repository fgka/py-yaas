# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
CLI entry point to test individual parts of the code.
"""
# pylint: enable=line-too-long
import asyncio
from datetime import datetime, timedelta
import functools
import io
import pathlib
from typing import Callable, Optional

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
from yaas.dto import request
from yaas.event.store import calendar, file
from yaas.gcp import cloud_run
from yaas.scaler import run, standard

# pylint: enable=wrong-import-position


_LOGGER = logger.get(__name__)


def coro(func: Callable):
    """
    A decorator to allow :py:module:`click` to play well with :py:module:`asyncio`.

    Source: https://github.com/pallets/click/issues/85#issuecomment-503464628
    Args:
        func:

    Returns:

    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.group(help="CLI entry point -- Description here.")
def cli() -> None:
    """
    Click entry-point.
    """


@cli.command(help="List upcoming events")
@click.option(
    "--calendar-id", required=True, type=str, help="Which calendar ID to read"
)
@click.option(
    "--json-creds", required=False, type=click.File("r"), help="JSON credentials file"
)
@click.option(
    "--start-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31"
)
@click.option(
    "--end-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31"
)
@click.option("--cache-file", required=False, type=str, help="Cache filename.")
@coro
async def list_events(
    calendar_id: str,
    json_creds: Optional[io.TextIOWrapper] = None,
    start_day: Optional[str] = None,
    end_day: Optional[str] = None,
    cache_file: Optional[str] = None,
) -> None:
    """
    List calendar events.

    Args:
        calendar_id: Google calendar ID
        json_creds: Google calendar JSON credentials
        start_day: From when to start listing the events
        end_day: Up until when to list events
        cache_file: Where to persist locally
    """
    # pylint: disable=too-many-locals,invalid-name,too-many-branches
    try:
        credentials_json = None
        if json_creds:
            credentials_json = pathlib.Path(json_creds.name).absolute()
        if start_day:
            start = datetime.fromisoformat(start_day)
        else:
            start = datetime.utcnow() - timedelta(days=2)
        if end_day:
            end = datetime.fromisoformat(end_day)
        else:
            end = datetime.utcnow()

        print(f"Date range: {start} {end}")

        cal_store = calendar.ReadOnlyGoogleCalendarStore(
            calendar_id=calendar_id, credentials_json=credentials_json
        )
        cal_snapshot = await cal_store.read(start_ts_utc=start, end_ts_utc=end)

        if cache_file:
            print(f"Caching events into <{cache_file}>")
            json_line_file = pathlib.Path(cache_file).absolute()
            archive_json_line_file = pathlib.Path(f"{cache_file}.archive").absolute()
            file_store = file.JsonLineFileStore(
                json_line_file=json_line_file,
                archive_json_line_file=archive_json_line_file,
            )
            await file_store.write(cal_snapshot, overwrite_within_range=True)
            await file_store.archive(
                start_ts_utc=0, end_ts_utc=start - timedelta(seconds=1)
            )
            cache_snapshot = await file_store.read(start_ts_utc=start, end_ts_utc=end)

        print(f"Snapshot {cal_snapshot.source} has")
        for ts, lst_req in cal_snapshot.timestamp_to_request.items():
            print(f"Timestamp {datetime.fromtimestamp(ts)} has {len(lst_req)} requests")
        if cache_file:
            print(f"Cache {cache_snapshot.source} has")
            for ts, lst_req in cache_snapshot.timestamp_to_request.items():
                print(
                    f"Timestamp {datetime.fromtimestamp(ts)} has {len(lst_req)} requests"
                )
            comp = (
                cache_snapshot.timestamp_to_request == cal_snapshot.timestamp_to_request
            )
            print("Comparison between calendar and cache: " f"{comp}")
            if not comp:
                print(f"Calendar: {cal_snapshot.source}")
                for ts, lst_req in cal_snapshot.timestamp_to_request.items():
                    print(
                        f"Timestamp {datetime.fromtimestamp(ts)} has {len(lst_req)} requests"
                    )
                    for req in lst_req:
                        print(f"\t{req}")
                print(f"Cache: {cache_snapshot.source}")
                for ts, lst_req in cache_snapshot.timestamp_to_request.items():
                    print(
                        f"Timestamp {datetime.fromtimestamp(ts)} has {len(lst_req)} requests"
                    )
                    for req in lst_req:
                        print(f"\t{req}")

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
@coro
async def scale_cloud_run(name: str, param: str, value: int) -> None:
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
    await scaler.enact()


@cli.command(help="Get Cloud Run service definition")
@click.option(
    "--name",
    type=str,
    help="Cloud Run service full resource name in the form:"
    "projects/MY_PROJECT/locations/MY_LOCATION/services/MY_SERVICE",
)
@coro
async def get_cloud_run(name: str) -> None:
    """
    Retrieves the service definition based on its name

    Args:
        name: service full-qualified name
    """
    result = await cloud_run.get_service(name)
    print(f"Service {name} resulted in:\n{result}\n")


if __name__ == "__main__":
    cli()
