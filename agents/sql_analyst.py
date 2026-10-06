import os
import sys
sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__) , '..')))

from utils.database import get_default_db_config

from typing import Literal
from utils.llm_pick import pick_llm
from models.schema import SQLAgentState , JudgeSchema
from utils.database import DatabaseUtil
from langchain_core.messages import HumanMessage , AIMessage, SystemMessage, ToolMessage

def extract_user_query(state:SQLAgentState):
    """Helper to extract user query string from user_message or the messages list."""
    if state.get("user_message"):
        return state["user_message"]
    messages = state.get("messages" , [])
    if messages:
        last = messages[-1]
        return last.content if hasattr(last ,"content") else str(last)
    return ""
# ------------- Agent Functions -------------

def curate_question(state:SQLAgentState) -> dict :
    """
    Curates and refines the user's question for precise SQL generation.
    """
    user_question = extract_user_query(state)
    llm = pick_llm("low")
    
    system_prompt = (
        "Rewrite the user's question into a clear, precise question suitable for "
        "generating a PostgreSQL query.\n"
        "Rules:\n"
        "- Preserve the user's original intent.\n"
        "- Do not add information or assumptions that are not present.\n"
        "- Do not answer the question.\n"
        "- Return only the rewritten question."
        f"user question : {user_question}"
    )
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_question)
    ])
    
    curated = response.content.strip()
    
    modified_dic = {
        "user_message":user_question,
        "curated_ques": curated
    }
    return modified_dic


def prompt_query_context(state: SQLAgentState) -> dict:
    """
    Retrieves PostgreSQL schema metadata and formats the prompt context for SQL generation.
    """
    curate_question = state.get("curated_ques") or extract_user_query(state)
    
    db_config = get_default_db_config()
    
    obj = DatabaseUtil(db_config=db_config)
    
    schema_info = obj.schema_details("public")

    return {
        "prompt_query_context": f"user query:\n{curate_question}\n\n database schema details:\n{schema_info}",

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
    
    context = state.get("prompt_query_context" , "")
    
    llm = pick_llm("medium")
    
    result = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ]).content
    
    cleaned_sql = result.replace("```sql", "").replace("```", "").strip()
    
    return {
        "generated_sql_query": cleaned_sql
    }


def is_safe_sql(state: SQLAgentState) -> dict:
    """
    Evaluates SQL query safety via an LLM judge to prevent destructive or mutating operations.
    """
    sql_query = state.get("generated_sql_query" , "")
    
    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)
    
    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate: {sql_query}"""
    
    judge_res = llm_judge.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"SQL query to evaluate : \n{sql_query}\n")
    ])
    
    answer = judge_res.answer
    comments = judge_res.comments
    
    return {
        "is_safe" :answer,
        "comments":comments
    }


def is_safe_sql_edge(state: SQLAgentState) -> Literal["execute_sql_edge" , "canceled_sql_edge"]:
    """
    Conditional routing function based on judge safety evaluation.
    """
    is_safe = state.get("is_safe" , "No") 
    
    if str(is_safe).strip().lower() == "yes" :
        return "execute_sql_edge"
    else:
        return "canceled_sql_edge"



# Executing the SQL (safe)
def execute_sql(state: SQLAgentState) -> dict :
    
    sql_query = state.get("generated_sql_query" , "")

    db_config = get_default_db_config()
    
    obj = DatabaseUtil(db_config=db_config)
    result = obj.execute_query(sql_query)
    
    return {
        "sql_query_execution_result" : str(result)
    }


# Cancelling SQL Query operation

def canceled_sql(state: SQLAgentState)-> dict:
    """
    Handles queries blocked by the safety judge, producing a final AIMessage.
    """
    comments = state.get("comments" , "Query did not pass safety validation.\n")
    
    final_answer = (
        f"The generated SQL query was deemed unsafe to execute. "
        f"Reason: {comments}. The query execution has been canceled."
    )
    return {
        "final_answer" : final_answer,
        "messages" : [AIMessage(content=final_answer)]
    }



def represent_final_answer(state: SQLAgentState)->dict:
    """
    Synthesizes the database query result into a natural, user-friendly AIMessage.
    """
    
    execution_result = state.get("sql_query_execution_result", "")
    curated_question = state.get("curated_ques", "")
    
    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """
    user_payload = (
        f"User's Question: {curated_question}\n\n"
        f"Query Execution Result:\n{execution_result}"
    )
    
    llm = pick_llm("low")
    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=user_payload)
    ])
    
    final_text = response.content.strip()
    
    return {
        "final_answer":final_text,
        "messages" : [AIMessage(content=final_text)]
    }