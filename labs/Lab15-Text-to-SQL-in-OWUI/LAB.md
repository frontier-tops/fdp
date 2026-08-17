# Lab 15 — Custom Text-to-SQL Pipeline in Open WebUI

**Duration** ~30 min · **GPU required** No · **Tool** Open WebUI at **http://10.79.253.112:3000**
**Verified** 🔴 **The `text_to_sql` pipeline is currently returning wrong answers** — see the
defect below. The notebook itself is documentation-only (1 cell); the problem is server-side.

## What this lab does
The same Text-to-SQL capability as Lab 14, delivered as a **pipeline inside Open WebUI** —
end users ask questions in a chat box and get answers from a database, with no code.

## Objectives
- Understand how a Text-to-SQL pipeline works end to end.
- Configure and use the pipeline within Open WebUI.
- Query a database in natural language and interpret the results.

## Access
**http://10.79.253.112:3000** — open on the participant VPN (verified 2026-08-15).

## 🔴 Known defect — do not demo this lab until it is fixed
Tested against the live pipeline on **17 Aug 2026**. It answers confidently and incorrectly,
which is the worst possible failure mode in front of a room:

| Asked | What happened |
|---|---|
| "How many rows are in the **album** table?" | Answered "**31 employees** currently recorded" — wrong table, wrong question, stated as fact |
| "List the top 5 artists by number of albums." | Generated `SELECT name FROM employees GROUP BY department ...` → `psycopg2.errors.UndefinedColumn: column "name" does not exist` |
| "How many albums are in the database?" | Passed the model's **prose** to the database as SQL → `psycopg2.errors.SyntaxError at or near "I"` |

Two distinct faults:
1. **Wrong database.** The pipeline is bound to a PostgreSQL instance containing an
   `employees` table — not the Chinook data this lab and Lab 14 describe.
2. **No SQL extraction or schema grounding.** The model's raw reply is executed directly, so
   plain English reaches the SQL parser, and the generated columns do not exist in the schema.

**For the facilitator:** check which datasource the `text_to_sql` pipeline is configured
against in the Pipelines server, point it at Chinook, confirm the schema is injected as
context, and ensure the pipeline extracts the SQL statement from the model output before
executing it. Until then, run **Lab 14** — which is verified working — and present Lab 15 as
a discussion of the pattern rather than a live demo.

> Lab 11's `langchain_pipeline` was tested at the same time and **works correctly**, so the
> Pipelines server itself is healthy; this is specific to `text_to_sql`.

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
