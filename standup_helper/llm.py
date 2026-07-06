import os
import re

from openai import OpenAI


def generate_standup(context: dict) -> str:
    client = OpenAI(
        api_key=os.environ["GOOGLE_AI_STUDIO_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    system_prompt = """Sei un assistente che aiuta a preparare il testo per lo standup mattutino.

Formato da seguire (adatta le sezioni in base ai dati disponibili):

Ieri sono stata su <nome progetto abbreviato>.
Ho completato le storie riguardo a:
- <descrizione storia, senza ID Jira>
- ...

[Se ci sono storie rifiutate/rejected:]
Ho avuto delle storie rifiutate:
- <descrizione storia>
- ...

[Se ci sono storie ancora in corso:]
Ho ancora a metà alcune storie, tra cui:
- <descrizione storia>
- ...

oggi conto di <cosa fare oggi, in base alle priorità: prima le storie rejected da sistemare, poi le storie in sospeso, poi eventualmente prenderne di nuove>.

Regole:
- Scrivi in prima persona femminile (sono stata, ho completato, ecc.)
- NON includere gli ID Jira nel testo finale
- Per il nome del progetto usa la forma abbreviata e riconoscibile (es: "Waterjade" invece di "MobyGis - Waterjade Digital Twin / Board MGWD", o "APCUP" invece di "APCUP - Agenda CUP / Board APCUP")
- Usa un tono naturale e colloquiale, come se lo dicessi a voce
- Ometti le sezioni che non hanno contenuto (es: se non ci sono rejected, non menzionarlo)
- Rispondi SOLO con il testo dello standup, senza preamboli o spiegazioni

PRIORITÀ DATI — fondamentale:
- Il lavoro di "ieri" (fatto, in corso, rifiutato) è SOLO quello elencato nella sezione "Lavoro tracciato su Toggl ieri". Toggl è l'unica fonte di verità su cosa è stato fatto.
- Lo stato Jira riportato accanto a ogni voce Toggl (es. "Stato: Done", "Stato: Rejected") serve SOLO a capire se quella storia già tracciata su Toggl è conclusa, ancora aperta, o rifiutata. Usalo per decidere in quale sezione del formato mettere quella storia (completate / rifiutate / in corso).
- La sezione "Altre storie sullo sprint" NON è lavoro di ieri: sono storie assegnate a me sulla board ma NON toccate ieri su Toggl. Non includerle MAI tra "ho completato" o "ho ancora a metà". Puoi usarle solo per la frase finale su cosa pensi di fare oggi, come eventuale storia nuova da prendere.
"""

    user_message = _build_context_message(context)

    response = client.chat.completions.create(
        model="gemma-4-31b-it",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    text = response.choices[0].message.content
    # strip internal reasoning blocks emitted by Gemma
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
    return text.strip()


def _build_context_message(context: dict) -> str:
    lines = [f"Data di riferimento: {context['date']}", ""]

    toggl_by_project = context.get("toggl_by_project", {})
    if toggl_by_project:
        lines.append("## Lavoro tracciato su Toggl ieri:")
        for proj_name, entries in toggl_by_project.items():
            lines.append(f"\n### {proj_name}")
            for e in entries:
                duration_min = e["duration_seconds"] // 60
                h, m = divmod(duration_min, 60)
                duration_str = f"{h}h {m:02d}m" if h else f"{m}m"
                jira_info = ""
                if e.get("jira"):
                    jira_info = f' [Jira: {e["jira"]["summary"]} — Stato: {e["jira"]["status"]}]'
                lines.append(f"- {e['description']} ({duration_str}){jira_info}")

    toggl_keys = {
        e.get("issue_key")
        for entries in toggl_by_project.values()
        for e in entries
    }

    in_progress = context.get("in_progress_issues", [])
    other_issues = [i for i in in_progress if i["key"] not in toggl_keys]

    if other_issues:
        lines.append(
            "\n## Altre storie sullo sprint (assegnate a me, NON lavorate ieri su Toggl — "
            "solo contesto board, non sono lavoro di ieri):"
        )
        for issue in other_issues:
            lines.append(
                f"- {issue['key']}: {issue['summary']}"
                f" (stato: {issue['status']}, progetto: {issue['project_name']} / board: {issue.get('board_name', 'n/a')})"
            )

    return "\n".join(lines)
