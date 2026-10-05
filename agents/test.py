import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import SystemMessage, HumanMessage
from models.schema import JudgeSchema
from utils.llm_pick import pick_llm


def is_safe_sql(sql: str):
    llm = pick_llm("low")
    llm_judge = llm.with_structured_output(JudgeSchema)

    system_prompt = (
        "You are an SQL Security Judge. Evaluate whether the following SQL query is safe to execute.\n"
        "The query must only perform read-only data retrieval (e.g. SELECT).\n"
        "It must not contain commands that alter data or schema (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE).\n"
        "Set answer to 'Yes' if safe, 'No' otherwise, with explanation in comments."
    )

    response = llm_judge.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"SQL Query to evaluate:\n{sql}")
    ])

    print("Result:", response.model_dump())
    return response


if __name__ == "__main__":
    sql = "DROP TABLE public.users CASCADE;"
    print("Testing SQL:", sql)
    is_safe_sql(sql=sql)