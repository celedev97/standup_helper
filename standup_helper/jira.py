import os
from functools import lru_cache

import requests
from requests.auth import HTTPBasicAuth


def _auth() -> HTTPBasicAuth:
    return HTTPBasicAuth(os.environ["JIRA_EMAIL"], os.environ["JIRA_API_TOKEN"])


def _base() -> str:
    return os.environ["JIRA_BASE_URL"].rstrip("/")


def _get(path: str, **kwargs) -> dict | list:
    resp = requests.get(f"{_base()}{path}", auth=_auth(), **kwargs)
    resp.raise_for_status()
    return resp.json()


@lru_cache(maxsize=1)
def _get_account_id() -> str:
    return _get("/rest/api/3/myself")["accountId"]


def get_issues(issue_keys: list[str]) -> dict[str, dict]:
    """Fetch details for a list of issue keys via direct GET (no JQL needed)."""
    result = {}
    for key in issue_keys:
        try:
            data = _get(f"/rest/api/3/issue/{key}",
                        params={"fields": "summary,status,project"})
            f = data["fields"]
            result[key] = {
                "summary": f["summary"],
                "status": f["status"]["name"],
                "status_category": f["status"]["statusCategory"]["key"],
                "project_key": f["project"]["key"],
                "project_name": f["project"]["name"],
            }
        except Exception:
            pass
    return result


# Statuses that mean "dev done, waiting for PO/QA" — not "in progress" for standup purposes
_DEV_DONE_STATUSES = {"developed"}


def get_in_progress_issues(project_keys: list[str]) -> list[dict]:
    """
    Get issues in active sprints for given projects, assigned to current user,
    that are not done (by Jira category) and not in a dev-done status.
    """
    account_id = _get_account_id()
    seen_keys: set[str] = set()
    result = []

    for project_key in project_keys:
        try:
            boards_data = _get("/rest/agile/1.0/board",
                               params={"projectKeyOrId": project_key, "maxResults": 10})
        except Exception:
            continue

        for board in boards_data.get("values", []):
            bid = board["id"]
            try:
                sprint_data = _get(f"/rest/agile/1.0/board/{bid}/sprint",
                                   params={"state": "active", "maxResults": 5})
            except Exception:
                continue

            for sprint in sprint_data.get("values", []):
                sid = sprint["id"]
                start = 0
                while True:
                    try:
                        issues_data = _get(
                            f"/rest/agile/1.0/sprint/{sid}/issue",
                            params={
                                "fields": "summary,status,project,assignee",
                                "maxResults": 50,
                                "startAt": start,
                            },
                        )
                    except Exception:
                        break

                    issues = issues_data.get("issues", [])
                    for issue in issues:
                        f = issue["fields"]
                        assignee = f.get("assignee") or {}
                        if assignee.get("accountId") != account_id:
                            continue
                        if f["status"]["statusCategory"]["key"] == "done":
                            continue
                        if f["status"]["name"].lower() in _DEV_DONE_STATUSES:
                            continue
                        key = issue["key"]
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        result.append({
                            "key": key,
                            "summary": f["summary"],
                            "status": f["status"]["name"],
                            "project_key": f["project"]["key"],
                            "project_name": f["project"]["name"],
                            "board_name": board["name"],
                        })

                    total = issues_data.get("total", 0)
                    start += len(issues)
                    if start >= total or not issues:
                        break

    return result
