# NL-to-SQL Analytics Tool

Ask a business question in plain English, get back validated SQL, real results from Postgres, an auto-generated chart, and a grounded natural-language summary — all through a browser.

**Live demo:** [your-streamlit-url].streamlit.app _(fill in after Streamlit Cloud deploy)_
**Backend API:** https://nlsql-analytics.fastapicloud.dev

Built on the [Pagila](https://github.com/devrimgunduz/pagila) dataset (a DVD rental store schema, the canonical PostgreSQL sample database) rather than a second e-commerce dataset, to keep this project's domain distinct from other portfolio work.

---

## Why this project exists

Text-to-SQL is genuinely hard to get right, and most portfolio projects that wire an LLM to a database stop at "it works on the demo question." This project is built around a different question: **when does it fail, and what can you actually do about it?**

Two independent pipelines are built and compared head-to-head:

- **Pipeline A — generate-then-validate:** the full database schema is given to the LLM, it generates SQL freely, and the result is checked against the real schema afterward (with one retry if validation fails).
- **Pipeline B — constrain-then-generate:** before the LLM ever sees a prompt, the schema is pruned down to only the tables relevant to the question, using keyword/synonym scoring. The same validation runs as a backstop.

Both pipelines share the same safety rail and schema validator, built with [SQLGlot](https://github.com/tobymao/sqlglot) — every generated query is parsed into an AST and checked for (a) read-only safety (no `DROP`/`DELETE`/etc. can ever reach the database, no exceptions) and (b) referencing only tables/columns that actually exist in the live schema, before it's ever executed.

## Architecture

Question -> Streamlit UI -> FastAPI backend -> Schema context (full or pruned)
-> Gemini (NL to SQL) -> SQLGlot validation (safety + schema check)
-> [fails -> logged / retried] [passes -> Postgres execution]
-> Results -> auto chart + LLM summary -> back to UI

## Tech stack

| Layer          | Choice                                                                                                                                   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Database       | PostgreSQL (Pagila schema), hosted on Supabase                                                                                           |
| LLM            | Google Gemini (`gemini-3.6-flash` for quality-sensitive calls, `gemini-flash-lite-latest` for bulk/eval work — see _Model choice_ below) |
| SQL validation | SQLGlot (AST parsing, schema + safety checks)                                                                                            |
| Backend        | FastAPI, deployed on FastAPI Cloud                                                                                                       |
| Frontend       | Streamlit, deployed on Streamlit Community Cloud                                                                                         |
| Local dev      | Docker Compose (Postgres + Pagila)                                                                                                       |

## Known limitations and real failures found

This section is deliberately honest rather than a highlight reel — these are actual bugs and edge cases found while building this, not hypothetical ones.

**1. Validator false positive on SELECT-clause aliases (found and fixed).**
Early testing showed the schema validator rejecting a completely valid query — `ORDER BY total_spent DESC` was flagged as an "unknown column" because `total_spent` was an alias created in the same query's `SELECT` clause, not a real database column. Postgres allows referencing SELECT aliases elsewhere in a query; the validator didn't know that. Fixed by having the validator collect all `SELECT`-clause aliases via SQLGlot's AST and exclude them from the unknown-column check, with a regression test confirming both the false positive and true positives are handled correctly afterward.

**2. Semantically valid answers can still be "incorrect" by the eval harness's strict comparison.**
For _"Compare total revenue between 2023 and 2024"_, Pipeline B returned a single-row pivot (`total_revenue_2023`, `total_revenue_2024` as two columns) instead of the gold answer's multi-row `GROUP BY year` format. Both are reasonable ways to answer the question — arguably the pivot is a _better_ answer to "compare" — but the eval script's row/column structure comparison flagged it as incorrect. This is a limitation of the **evaluation methodology**, not necessarily the model: automated grading struggles to recognize that two structurally different queries can answer a question equally well.

**3. Logically correct SQL can still omit information the question implied.**
For _"top 5 customers by total amount spent,"_ one generation correctly joined, grouped, and sorted by spend — but only selected customer names, dropping the actual spend amount from the output. The query's logic was entirely correct; the output was incomplete. Schema validation has no way to catch this, since the query is 100% valid — it's a different failure category from hallucinated tables/columns.

**4. Schema noise from physical table partitioning.**
The `payment` table is partitioned by month (50+ `payment_p2022_01`-style physical tables). Left unfiltered, these flooded the LLM's schema context with near-duplicate, non-business-meaningful tables. Fixed by excluding partition tables from schema introspection entirely — the LLM only ever sees the logical `payment` table, and Postgres handles routing queries to the correct partition transparently.

**5. Naive keyword-based schema pruning can false-positive on short words.**
Pipeline B's table-relevance scorer initially matched the word "in" (from "revenue **in** 2023") against `inventory` and `inventory_id` as substrings, pulling in irrelevant tables. Fixed with a stopword filter and a minimum token length before scoring.

**6. Free-tier LLM API quotas are a real constraint, not a footnote.**
Google cut Gemini's free-tier daily quota for `gemini-3.6-flash` from roughly 250-500/day down to just 20/day in a December 2025 policy change. A single full evaluation run (17 questions x 2 pipelines, with retries) needs 35-45+ calls — comfortably exceeding that in one sitting. Solved by routing bulk/eval traffic to `gemini-flash-lite-latest` (a much higher free quota) while keeping the single, user-facing summary call on the stronger model, since one call per question isn't quota-sensitive the way a 40-call eval batch is.

**7. Local dev environment fought a moving target.**
Pagila's `master` branch schema uses several PostgreSQL 18-only features (`uuidv7()`, `GENERATED ... VIRTUAL` columns, `transaction_timeout`) and a `pgvector` extension not present in a stock `postgres:16` Docker image. Working locally required either patching the schema for compatibility (used for the Supabase deploy, which runs an older Postgres version) or switching to `pgvector/pgvector:pg18` with a corrected volume mount path (used for local dev). Both paths are documented in `data/pagila/` (local, PG18) vs `data/pagila_deploy/` (patched, PG17-compatible).

## Evaluation results

Full results in `eval/results/`. **Note:** due to free-tier quota limits during testing, the most complete single run covered 8 of 17 gold questions before hitting a quota wall (see limitation #6). Numbers below are from that partial run; re-running the full 17-question set is a natural next step.

| Pipeline                    | Valid rate | Correct rate | Avg. attempts |
| --------------------------- | ---------- | ------------ | ------------- |
| generate_then_validate (A)  | 52.9%      | 23.5%        | 1.0           |
| constrain_then_generate (B) | 52.9%      | 23.5%        | 1.11          |

Both pipelines currently show identical aggregate rates on partial data, but diverged meaningfully on individual questions (see limitations #2-3 above) — the aggregate numbers alone understate how differently the two approaches behave case by case.

## Project structure

nlsql-analytics/
|-- backend/
| |-- main.py FastAPI app (/health, /ask)
| |-- nl2sql/ Pipeline A + B, prompts, Gemini client
| |-- schema/ Schema introspection + pruning
| |-- validation/ SQLGlot safety + schema checks
| |-- execution/ SQL execution against Postgres
| -- output/ Chart picker, NL summarizer |-- frontend/ | -- app.py Streamlit UI
|-- eval/
| |-- gold_questions.yaml 17 hand-verified question/answer pairs
| |-- run_eval.py Runs both pipelines against gold set
| -- results/ Eval run outputs (JSON + summary CSV) |-- data/ | |-- pagila/ PG18-compatible schema/data (local dev) | -- pagila_deploy/ PG17-compatible schema/data (Supabase)
|-- docker-compose.yml
`-- main.py Entry point for FastAPI Cloud deployment

## Running it locally

**Prerequisites:** Docker Desktop, Python 3.11+, a free [Gemini API key](https://aistudio.google.com/apikey).

```powershell
git clone https://github.com/SereneSkyy/nlsql-analytics.git
cd nlsql-analytics

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env
# then edit .env with your real DATABASE_URL and GEMINI_API_KEY

docker compose up -d
# wait ~30-60s for Pagila to finish loading, then verify:
docker exec -it nlsql_postgres psql -U postgres -d pagila -c "\dt"
```

In one terminal, start the backend:

```powershell
uvicorn backend.main:app --reload
```

In a second terminal, start the frontend:

```powershell
streamlit run frontend\app.py
```

Open the Streamlit URL it prints (typically `http://localhost:8501`) and ask a question.

### Running the evaluation harness

```powershell
$env:GEMINI_MODEL = "gemini-flash-lite-latest"
python eval\run_eval.py
```

Results are written to `eval/results/` as timestamped JSON (full detail) and CSV (summary).

## Deployment

- **Database:** Supabase (managed Postgres, Pagila loaded via the patched files in `data/pagila_deploy/`)
- **Backend:** FastAPI Cloud (`fastapi deploy`), secrets managed via `fastapi cloud env set`
- **Frontend:** Streamlit Community Cloud, configured with `API_URL` in its secrets pointing at the live backend

---

Built by Saurav Khanal.
