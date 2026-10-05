#  Multi-Agent SQL Analyst & ETL Engine

An intelligent, multi-agent architecture powered by **LangGraph**, **LangChain**, and **Groq LLMs**. The system routes user natural language queries between specialized sub-graphs to handle database querying (Text-to-SQL) and automated Data Engineering/ETL pipelines safely.

---

##  Key Features

- ** Smart Workflow Routing:** Automatically evaluates incoming requests using a structured router and dispatches them to either the SQL Analyst or ETL Agent graph.
- ** Guardrailed Text-to-SQL Pipeline:**
  - **Question Refinement:** Rephrases user prompts into clean, clear SQL requirements.
  - **Dynamic Schema Inspection:** Automatically extracts tables, column definitions, data types, and sample rows from PostgreSQL schemas (`public`).
  - **Security Judge Node:** Evaluates generated SQL queries against strict DDL/DML restrictions (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.) before execution.
  - **Result Synthesis:** Formats raw query execution tuples into friendly, executive summaries.
- ** Autonomous ETL & Data Pipeline Engine:**
  - **REST API Data Ingestion:** Extracts data from external API endpoints into structured `.csv`, `.json`, or `.parquet` formats.
  - **Dynamic Code Generation & Execution:** Generates and runs Pandas transformation scripts in isolated scopes based on data context inspection.

---

##  System Architecture

```
                    ┌────────────────────────┐
                    │   User Input Query     │
                    └───────────┬────────────┘
                                │
                        ┌───────▼────────┐
                        │  Router Node   │
                        └───────┬────────┘
                                │
             ┌──────────────────┴──────────────────┐
             │                                     │
      [ Route: "sql" ]                      [ Route: "etl" ]
             │                                     │
    ┌────────▼─────────┐                  ┌────────▼────────┐
    │ SQL Analyst Graph│                  │ ETL Analyst    │
    └────────┬─────────┘                  │ Sub-Graph      │
             │                            └────────┬────────┘
  ┌──────────┼──────────┐                          │
  │ Curate   │ Schema   │                  ┌───────▼────────┐
  │ Query    │ Context  │                  │ LLM Tool-Call  │
  └──────────┼──────────┘                  └───────┬────────┘
             │                                     │
  ┌──────────▼──────────┐                 ┌────────┴────────┐
  │  SQL Generator      │                 │ API Extract /   │
  └──────────┬──────────┘                 │ Pandas Code Exec│
             │                            └─────────────────┘
  ┌──────────▼──────────┐
  │ Security Judge Node │
  └──────────┬──────────┘
        Is Safe?
      /        \
   (Yes)       (No)
    │            │
 ┌──▼──────┐  ┌──▼───────────┐
 │ Execute │  │ Cancel Query │
 └──┬──────┘  └──────────────┘
    │
 ┌──▼────────────┐
 │ Format Answer │
 └───────────────┘
```

---

## 🛠️ Tech Stack

- **Orchestration:** [LangGraph](https://github.com/langchain-ai/langgraph), [LangChain](https://github.com/langchain-ai/langchain)
- **Models:** Groq API (`openai/gpt-oss-120b`, `qwen/qwen3.8-27b`)
- **Database:** PostgreSQL via `psycopg2`
- **Data Transformation & Processing:** Pandas, PyArrow (Parquet)
- **Validation & Schemas:** Pydantic v2
- **Environment Management:** Python `dotenv`


---

## 🔒 Security & Guardrails

The **SQL Security Judge** prevents unauthorized database modifications. Any generated query is inspected for unsafe keywords before execution:

- **Forbidden Statements:** `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, etc.
- **Action on Violation:** If flagged, the query execution step is bypassed, and a detailed explanation is returned to the user without touching the database.

---

