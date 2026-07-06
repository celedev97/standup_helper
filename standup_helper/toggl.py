import os
import re
from datetime import date, timedelta

import requests
from requests.auth import HTTPBasicAuth


def get_last_working_day(today: date | None = None) -> date:
    d = today or date.today()
    delta = 1
    if d.weekday() == 0:  # Monday → Friday
        delta = 3
    elif d.weekday() == 6:  # Sunday → Friday
        delta = 2
    return d - timedelta(days=delta)


def find_last_date_with_entries(starting_from: date | None = None, max_lookback_days: int = 14) -> tuple[date, list[dict]]:
    d = starting_from or get_last_working_day()
    for _ in range(max_lookback_days):
        entries = get_time_entries(d)
        if entries:
            return d, entries
        d -= timedelta(days=1)
        if d.weekday() == 6:  # skip Sunday
            d -= timedelta(days=1)
        if d.weekday() == 5:  # skip Saturday
            d -= timedelta(days=1)
    return d, []


def get_time_entries(target_date: date | None = None) -> list[dict]:
    token = os.environ["TOGGL_API_TOKEN"]
    target = target_date or get_last_working_day()

    # Use UTC+0 range; Toggl stores in UTC and Europe/Berlin offset (~2h) keeps
    # working-hour entries on the correct calendar date.
    start = target.isoformat() + "T00:00:00+00:00"
    end = target.isoformat() + "T23:59:59+00:00"

    resp = requests.get(
        "https://api.track.toggl.com/api/v9/me/time_entries",
        params={"start_date": start, "end_date": end},
        auth=HTTPBasicAuth(token, "api_token"),
    )
    resp.raise_for_status()
    entries = resp.json()

    issue_pattern = re.compile(r"^([A-Z]+-\d+)")
    result = []
    for entry in entries:
        description = (entry.get("description") or "").strip()
        match = issue_pattern.match(description)
        result.append(
            {
                "description": description,
                "issue_key": match.group(1) if match else None,
                "project_key": match.group(1).split("-")[0] if match else None,
                "duration_seconds": max(entry.get("duration", 0), 0),
            }
        )
    return result
