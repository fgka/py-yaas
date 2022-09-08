# Source: https://developers.google.com/calendar/api/quickstart/python
from __future__ import print_function

import datetime
import click

from googleapiclient import sample_tools
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/calendar.readonly",
]

@click.group(help="CLI to read a calendar")
def cli() -> None:
    """
    Click entry-point
    """


@cli.command(help="List upcoming events")
@click.option("--calendar-id", required=True, type=str, help="Which calendar to read.")
def list_events(calendar_id: str):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        service = _build_service([])
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        print("An error occurred: %s" % error)


def _build_service(argv):
    service, flags = sample_tools.init(
        argv,
        "calendar",
        "v3",
        __doc__,
        __file__,
        scope="https://www.googleapis.com/auth/calendar.readonly",
    )
    return service


if __name__ == "__main__":
    cli()
