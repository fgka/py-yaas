# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""CLI entry point to test individual parts of the code."""
import asyncio
import functools
import pathlib
from datetime import datetime, timedelta
from typing import Callable, Optional, Tuple

import click
from yaas_caching import calendar, event, gcs
from yaas_calendar import google_cal
from yaas_common import logger, request
from yaas_gcp import cloud_run
from yaas_scaler import run, standard

_LOGGER = logger.get(__name__)


def coro(func: Callable):
    """A decorator to allow :py:module:`click` to play well with
    :py:module:`asyncio`.

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
    """Click entry-point."""


@cli.command(help="List upcoming events")
@click.option("--calendar-id", required=True, type=str, help="Which calendar ID to read")
@click.option("--secret-name", required=False, type=str, help="Secret name with credentials")
@click.option("--start-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31")
@click.option("--end-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31")
@click.option("--project", required=False, type=str, help="Google Cloud project")
@click.option("--bucket-name", required=False, type=str, help="Bucket where to store the cache.")
@click.option(
    "--db-object",
    required=False,
    type=str,
    help="Path in the bucket where to store the cache object.",
)
@coro
async def list_events(
    calendar_id: str,
    secret_name: Optional[str] = None,
    start_day: Optional[str] = None,
    end_day: Optional[str] = None,
    project: Optional[str] = None,
    bucket_name: Optional[str] = None,
    db_object: Optional[str] = None,
) -> None:
    """List calendar events.

    Args:
        calendar_id: Google calendar ID
        secret_name: Google calendar JSON credentials
        start_day: From when to start listing the events
        end_day: Up until when to list events
        project: Project ID
        bucket_name: Where to persist in GCS
        db_object: Where to persist locally
    """
    try:
        start_ts_utc, end_ts_utc = await _start_end_ts_utc_from_iso_str(
            start_iso_format=start_day, end_iso_format=end_day
        )
        print(f"Date range: {start_ts_utc} {end_ts_utc}")
        cal_snapshot = await _calendar_snapshot(
            calendar_id=calendar_id,
            secret_name=secret_name,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
        )
        print(f"Snapshot {cal_snapshot.source} has")
        cache_snapshot = await _cache_snapshot(
            project=project,
            bucket_name=bucket_name,
            db_object=db_object,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
            cal_snapshot=cal_snapshot,
        )
        for ts_utc, lst_req in cal_snapshot.timestamp_to_request.items():
            print(f"Timestamp {datetime.fromtimestamp(ts_utc)} has {len(lst_req)} requests")
        if cache_snapshot:
            await _compare_snapshots(cal_snapshot=cal_snapshot, cache_snapshot=cache_snapshot)
    except Exception as err:  # pylint: disable=broad-except
        print(f"An error occurred: {err}")


async def _start_end_ts_utc_from_iso_str(
    *, start_iso_format: Optional[str] = None, end_iso_format: Optional[str] = None
) -> Tuple[int, int]:
    if start_iso_format:
        start_ts_utc = datetime.fromisoformat(start_iso_format)
    else:
        start_ts_utc = datetime.utcnow() - timedelta(days=2)
    if end_iso_format:
        end_ts_utc = datetime.fromisoformat(end_iso_format)
    else:
        end_ts_utc = datetime.utcnow()
    return start_ts_utc, end_ts_utc


async def _calendar_snapshot(
    *, calendar_id: str, secret_name: str, start_ts_utc: int, end_ts_utc: int
) -> event.EventSnapshot:
    result = calendar.ReadOnlyGoogleCalendarStore(calendar_id=calendar_id, secret_name=secret_name)
    async with result as obj:
        cal_snapshot = await obj.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
    return cal_snapshot


async def _cache_snapshot(
    *,
    project: str,
    bucket_name: str,
    db_object: str,
    start_ts_utc: int,
    end_ts_utc: int,
    cal_snapshot: Optional[event.EventSnapshot] = None,
) -> event.EventSnapshot:
    result = None
    if bucket_name and db_object:
        print(f"Events cache: bucket <{bucket_name}> and object <{db_object}>")
        gcs_store = gcs.GcsObjectStoreContextManager(
            bucket_name=bucket_name,
            db_object_path=db_object,
            project=project,
        )
        if isinstance(cal_snapshot, event.EventSnapshot):
            async with gcs_store as obj:
                await obj.write(cal_snapshot, overwrite_within_range=True)
                await obj.archive(start_ts_utc=0, end_ts_utc=start_ts_utc - timedelta(seconds=1))
        async with gcs_store as obj:
            result = await obj.read(start_ts_utc=start_ts_utc, end_ts_utc=end_ts_utc)
    return result


async def _compare_snapshots(*, cal_snapshot: event.EventSnapshot, cache_snapshot: event.EventSnapshot) -> None:
    print(f"Cache {cache_snapshot.source} has")
    for ts_utc, lst_req in cache_snapshot.timestamp_to_request.items():
        print(f"Timestamp {datetime.fromtimestamp(ts_utc)} has {len(lst_req)} requests")
    comp = cache_snapshot.timestamp_to_request == cal_snapshot.timestamp_to_request
    print("Comparison between calendar and cache: " f"{comp}")
    if not comp:
        print(f"Calendar: {cal_snapshot.source}")
        for ts_utc, lst_req in cal_snapshot.timestamp_to_request.items():
            print(f"Timestamp {datetime.fromtimestamp(ts_utc)} has {len(lst_req)} requests")
            for req in lst_req:
                print(f"\t{req}")
        print(f"Cache: {cache_snapshot.source}")
        for ts_utc, lst_req in cache_snapshot.timestamp_to_request.items():
            print(f"Timestamp {datetime.fromtimestamp(ts_utc)} has {len(lst_req)} requests")
            for req in lst_req:
                print(f"\t{req}")


@cli.command(help="Apply requests")
@click.option("--start-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31")
@click.option("--end-day", required=False, type=str, help="ISO formatted date, like: 2001-12-31")
@click.option("--project", required=False, type=str, help="Google Cloud project")
@click.option("--bucket-name", required=False, type=str, help="Bucket where to store the cache.")
@click.option(
    "--db-object",
    required=False,
    type=str,
    help="Path in the bucket where to store the cache object.",
)
@coro
async def apply_events(
    start_day: Optional[str] = None,
    end_day: Optional[str] = None,
    project: Optional[str] = None,
    bucket_name: Optional[str] = None,
    db_object: Optional[str] = None,
) -> None:
    """

    Args:
        start_day:
        end_day:
        project:
        bucket_name:
        db_object:

    Returns:

    """
    try:
        start_ts_utc, end_ts_utc = await _start_end_ts_utc_from_iso_str(
            start_iso_format=start_day, end_iso_format=end_day
        )
        print(f"Date range: {start_ts_utc} {end_ts_utc}")
        cache_snapshot = await _cache_snapshot(
            project=project,
            bucket_name=bucket_name,
            db_object=db_object,
            start_ts_utc=start_ts_utc,
            end_ts_utc=end_ts_utc,
        )
        parser = standard.StandardScalingCommandParser()
        await parser.enact(
            *[req for req_lst in cache_snapshot.timestamp_to_request.values() for req in req_lst],
            raise_if_invalid_request=False,
        )
    except Exception as err:  # pylint: disable=broad-except
        print(f"An error occurred: {err}")


async def _enact_request(parser: standard.StandardScalingCommandParser, req: request.ScaleRequest) -> None:
    try:
        scaler = parser.scaler(req)
        await scaler.enact()
    except Exception as err:  # pylint: disable=broad-except
        print(f"Could not apply request <{req}>. Error: {err}")


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
    type=click.Choice([param.value for param in run.CloudRunCommandType]),
    help="Which scaling parameter to set",
)
@click.option("--value", required=True, type=int, help="Value to be set to the parameter")
@coro
async def scale_cloud_run(name: str, param: str, value: int) -> None:
    """Create a :py:cls:`request.ScaleRequest` and, from this request, a
    :py:cls:`run.CloudRunScaler` based on the arguments. It uses the scaler to
    enact the request.

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
    """Retrieves the service definition based on its name.

    Args:
        name: service full-qualified name
    """
    result = await cloud_run.get_service(name)
    print(f"Service {name} resulted in:\n{result}\n")


@cli.command(help="Updates the Google Calendar credentials to include user authorization.")
@click.option("--calendar-id", required=True, type=str, help="Which calendar ID to read")
@click.option("--secret-name", required=False, type=str, help="Secret name with credentials")
@click.option(
    "--credentials-json",
    required=False,
    type=str,
    help="Google Calendar initial credentials JSON file",
)
@coro
async def update_calendar_credentials(
    calendar_id: str,
    secret_name: Optional[str] = None,
    credentials_json: Optional[str] = None,
) -> None:
    """Will update the credentials for Google Calendar, if needed.

    Args:
        calendar_id: Google calendar ID
        secret_name: Google calendar JSON credentials
        credentials_json: JSON file retrieved from Google Calendar account

    Returns:
    """
    actual_credentials_json = None
    if credentials_json:
        actual_credentials_json = pathlib.Path(credentials_json).absolute()
    try:
        await google_cal.update_secret_credentials(
            calendar_id=calendar_id,
            secret_name=secret_name,
            initial_credentials_json=actual_credentials_json,
        )
    except Exception as err:  # pylint: disable=broad-except
        print(f"An error occurred: {err}")


if __name__ == "__main__":
    cli()
