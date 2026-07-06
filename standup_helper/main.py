import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from standup_helper import jira, llm, toggl


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Genera il testo per lo standup mattutino.")
    parser.add_argument(
        "--date",
        help="Data da usare (YYYY-MM-DD). Default: ultimo giorno lavorativo.",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra solo i dati raccolti senza chiamare l'LLM.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Stampa solo il testo a terminale, senza salvare il file né aprire Notepad.",
    )
    args = parser.parse_args()

    target_date: date | None = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Errore: formato data non valido '{args.date}'. Usa YYYY-MM-DD.")
            sys.exit(1)

    print("Fetching Toggl...", end=" ", flush=True)
    if target_date:
        entries = toggl.get_time_entries(target_date)
        effective_date = target_date
    else:
        effective_date, entries = toggl.find_last_date_with_entries()

    print(f"{len(entries)} entries trovate.")
    print(f"Raccolta dati per: {effective_date.strftime('%A %d %B %Y')}\n")

    issue_keys = [e["issue_key"] for e in entries if e["issue_key"]]

    print("Fetching Jira issues da Toggl...", end=" ", flush=True)
    jira_issues = jira.get_issues(issue_keys) if issue_keys else {}
    print(f"{len(jira_issues)} issue trovate.")

    project_keys = list({e["project_key"] for e in entries if e["project_key"]})
    print("Fetching Jira In Progress...", end=" ", flush=True)
    in_progress = jira.get_in_progress_issues(project_keys)
    print(f"{len(in_progress)} storie in corso.")

    toggl_by_project: dict[str, list] = {}
    for entry in entries:
        jira_detail = jira_issues.get(entry["issue_key"]) if entry["issue_key"] else None
        proj_name = (
            jira_detail["project_name"]
            if jira_detail
            else (entry["project_key"] or "Senza progetto")
        )
        entry["jira"] = jira_detail
        toggl_by_project.setdefault(proj_name, []).append(entry)

    context = {
        "date": effective_date.isoformat(),
        "toggl_by_project": toggl_by_project,
        "in_progress_issues": in_progress,
    }

    if args.dry_run:
        import json
        print("\n--- RAW CONTEXT ---")
        print(json.dumps(context, indent=2, ensure_ascii=False, default=str))
        return

    print("\nGenerazione standup...\n")
    text = llm.generate_standup(context)
    print("=" * 50)
    print(text)
    print("=" * 50)

    if args.stdout:
        return

    output_dir = Path.home() / "Documents" / "Standup"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{date.today().isoformat()}_standup.txt"
    output_file.write_text(text, encoding="utf-8")
    print(f"\nSalvato in: {output_file}")

    subprocess.Popen(["notepad.exe", str(output_file)])


if __name__ == "__main__":
    main()
