# Lab 15 — Custom Text-to-SQL Pipeline in Open WebUI

**Duration** ~30 min · **GPU required** No · **Tool** Open WebUI at **http://10.79.253.112:3000**
**Verified** ✅ Documentation-only notebook (1 cell).

## What this lab does
The same Text-to-SQL capability as Lab 14, delivered as a **pipeline inside Open WebUI** —
end users ask questions in a chat box and get answers from a database, with no code.

## Objectives
- Understand how a Text-to-SQL pipeline works end to end.
- Configure and use the pipeline within Open WebUI.
- Query a database in natural language and interpret the results.

## Access
**http://10.79.253.112:3000** — open on the participant VPN (verified 2026-08-15).

## How Text-to-SQL works
1. The user asks a question in natural language.
2. The **schema** is supplied to the model as context.
3. The model generates a SQL statement.
4. The pipeline executes it against the database.
5. Results are returned to the model, which phrases a natural-language answer.

## Walkthrough
1. **Log in** to Open WebUI.
2. **Select the Text-to-SQL pipeline/model** from the dropdown.
3. **Ask a question** in plain English about the dataset.
4. **Inspect the generated SQL** — most pipelines display it; verify it matches the intent.
5. **Compare with Lab 14** — same pattern, but the toolkit wiring is hidden.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Pipeline missing from the dropdown | Not enabled on the server — ask the facilitator. |
| Answers ignore the database | The plain chat model is selected instead of the pipeline. |
| SQL errors surfaced in chat | Schema mismatch; check which database is connected. |

## Teaching notes
Close the agentic track with this: Lab 14 shows the mechanism, Lab 15 shows the product.
Good moment to ask faculty how they would deploy such a tool for students — and what could
go wrong if it had write access.
