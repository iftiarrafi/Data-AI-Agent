import os
import sys
from typing import Literal

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from utils.llm_pick import pick_llm
from models.schema import SQLAgentState, JudgeSchema
from utils.database import DatabaseUtil


def _extract_user_query(state: SQLAgentState) -> str:
    """Helper to extract user query string from user_message or the messages list."""
    if state.get("user_message"):
        return state["user_message"]
    messages = state.get("messages", [])
    if messages:
        last = messages[-1]
        return last.content if hasattr(last, "content") else str(last)
    return ""


# ------------- Agent Nodes -------------

def curate_question(state: SQLAgentState) -> dict:
    """
    Curates and refines the user's question for precise SQL generation.
    """
    user_question = _extract_user_query(state)
    llm = pick_llm("low")

    system_prompt = (
        "Rewrite the user's question into a clear, precise question suitable for "
        "generating a PostgreSQL query.\n"
        "Rules:\n"
        "- Preserve the user's original intent.\n"
        "- Do not add information or assumptions that are not present.\n"
        "- Do not answer the question.\n"
        "- Return only the rewritten question."
    )

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_question)
    ])

    curated = response.content.strip()
    return {
        "user_message": user_question,
        "curated_ques": curated
    }


def prompt_query_context(state: SQLAgentState) -> dict:
    """
    Retrieves PostgreSQL schema metadata and formats the prompt context for SQL generation.
    """
    curated_question = state.get("curated_ques") or _extract_user_query(state)
    db = DatabaseUtil()
    schema_info = db.schema_details("public")

    system_prompt = (
        "You are an expert SQL analyst agent. Your task is to convert the user's natural language "
        "query into an executable PostgreSQL query based on the schema.\n"
        "Rules:\n"
        "- Unless the user explicitly asks for a specific number of rows, always limit the output to 10 rows.\n"
        "- Return ONLY the raw SQL query.\n"
        "- Do NOT wrap the query in markdown (no ```sql or ```).\n"
        "- Do NOT include any explanations, markdown formatting, or comments.\n"
        "- The first character of your response must be the beginning of the SQL query.\n"
        "- The last character must be the end of the SQL query."
    )

    user_payload = (
        f"User Query:\n{curated_question}\n\n"
        f"Database Schema Details:\n{schema_info}"
    )

    return {
        "prompt_query_context": user_payload,
        "system_prompt": system_prompt
    }


def generate_sql(state: SQLAgentState) -> dict:
    """
    Generates a PostgreSQL query using the curated question and schema context.
    """
    system_prompt = (
        "You are an expert SQL analyst agent. Your task is to convert the user's natural language "
        "query into an executable PostgreSQL query based on the schema.\n"
        "Rules:\n"
        "- Unless the user explicitly asks for a specific number of rows, always limit the output to 10 rows.\n"
        "- Return ONLY the raw SQL query.\n"
        "- Do NOT wrap the query in markdown (no ```sql or ```).\n"
        "- Do NOT include any explanations, markdown formatting, or comments.\n"
        "- The first character of your response must be the beginning of the SQL query.\n"
        "- The last character must be the end of the SQL query."
    )
    user_payload = state.get("prompt_query_context", "")
    llm = pick_llm("medium")

    result = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_payload)
    ]).content

    cleaned_sql = result.replace("```sql", "").replace("```", "").strip()

    return {"generated_sql_query": cleaned_sql}


def is_safe_sql(state: SQLAgentState) -> dict:
    """
    Evaluates SQL query safety via an LLM judge to prevent destructive or mutating operations.
    """
    sql_query = state.get("generated_sql_query", "")
    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)

    system_prompt = (
        "You are an SQL Security Judge. Determine whether the following SQL query is safe to execute.\n"
        "The SQL query must only perform read-only data retrieval (e.g. SELECT).\n"
        "It MUST NOT contain any commands that mutate data or schema "
        "(INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE).\n"
        "If safe and read-only, set answer to 'Yes', otherwise 'No'. Explain in comments."
    )

    judge_res = llm_judge.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"SQL Query to evaluate:\n{sql_query}")
    ])

    return {
        "is_safe": judge_res.answer,
        "comments": judge_res.comments
    }


def is_safe_sql_edge(state: SQLAgentState) -> Literal["execute_sql", "canceled_sql"]:
    """
    Conditional routing function based on judge safety evaluation.
    """
    is_safe = state.get("is_safe", "No")
    if str(is_safe).strip().lower() == "yes":
        return "execute_sql"
    return "canceled_sql"


def execute_sql(state: SQLAgentState) -> dict:
    """
    Executes the approved SQL query against PostgreSQL.
    """
    sql_query = state.get("generated_sql_query", "")
    db = DatabaseUtil()
    result = db.execute_query(sql_query)

    return {"sql_query_execution_result": str(result)}


def canceled_sql(state: SQLAgentState) -> dict:
    """
    Handles queries blocked by the safety judge, producing a final AIMessage.
    """
    comments = state.get("comments", "Query did not pass safety validation.")
    final_answer = (
        f"The generated SQL query was deemed unsafe to execute. "
        f"Reason: {comments}. The query execution has been canceled."
    )
    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)]
    }


def represent_final_answer(state: SQLAgentState) -> dict:
    """
    Synthesizes the database query result into a natural, user-friendly AIMessage.
    """
    execution_result = state.get("sql_query_execution_result", "")
    curated_question = state.get("curated_ques", "")

    system_prompt = (
        "You are an SQL analyst assistant. Provide a clear, helpful, and concise final answer "
        "to the user based on the database query execution result and the user's question.\n"
        "Do NOT include raw SQL syntax or technical database errors in your final text. "
        "Present the findings in a friendly, professional manner."
    )
    user_payload = (
        f"User's Question: {curated_question}\n\n"
        f"Query Execution Result:\n{execution_result}"
    )

    llm = pick_llm("low")
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_payload)
    ])
    final_text = response.content.strip()

    return {
        "final_answer": final_text,
        "messages": [AIMessage(content=final_text)]
    }