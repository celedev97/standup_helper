# Standup Helper

A CLI tool that generates your daily standup text automatically, by pulling
yesterday's tracked time from [Toggl Track](https://toggl.com/track/) and
cross-referencing it with issue status from Jira, then feeding it all to an
LLM to produce a natural-sounding standup update.

## How it works

1. Fetches yesterday's (or a given date's) time entries from Toggl.
2. Looks up the matching Jira issues (parsed from the entry description,
   e.g. `PROJ-123 did the thing`) to know their status (Done, Rejected,
   In Progress, ...).
3. Also fetches other issues assigned to you in the active sprint that
   weren't tracked yesterday, as extra context for "what to pick up today".
4. Sends everything to an LLM (any OpenAI-compatible endpoint) which writes
   the standup text in first person.
5. Prints the result, saves it to `~/Documents/Standup/<date>_standup.txt`,
   and opens it in Notepad.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate  # or source .venv/bin/activate on Linux/macOS
pip install -e .
```

Copy `.env.example` to `.env` and fill in your own values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `TOGGL_API_TOKEN` | Your Toggl Track API token (Profile settings → API Token). |
| `JIRA_BASE_URL` | Your Jira/Atlassian site URL, e.g. `https://yourcompany.atlassian.net`. |
| `JIRA_EMAIL` | Email used to log into Jira. |
| `JIRA_API_TOKEN` | Jira API token (generated from your Atlassian account). |
| `LLM_API_KEY` | API key for your LLM provider. |
| `LLM_BASE_URL` | Base URL of any OpenAI-compatible chat completions endpoint (Google AI Studio, OpenAI, a local Ollama server, etc.). |
| `LLM_MODEL` | Model name to use for generation. |
| `USER_GENDER` | `f` or `m` — controls the grammatical gender used in the generated Italian text (e.g. "stata"/"stato"). |

## Usage

```bash
standup
```

Options:

- `--date YYYY-MM-DD` — generate the standup for a specific date instead of
  the last working day.
- `--dry-run` — print the raw collected data (Toggl + Jira) as JSON without
  calling the LLM.

## Notes

- Standup text is generated in Italian (the prompt/output language is
  currently hardcoded in `standup_helper/llm.py`).
- Jira issue keys are detected from time entry descriptions that start with
  a pattern like `PROJ-123`.
- Requires "In Progress"-style workflows on active sprints; issues in a
  Done status category are excluded automatically.
