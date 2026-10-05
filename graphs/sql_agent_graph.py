import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, START, END
from models.schema import SQLAgentState
from agents.sql_analyst import (
    curate_question,
    prompt_query_context,
    generate_sql,
    is_safe_sql,
    is_safe_sql_edge,
    execute_sql,
    canceled_sql,
    represent_final_answer,
)

# Initialize the StateGraph using SQLAgentState with add_messages reducer
graph = StateGraph(SQLAgentState)

# Add processing nodes
graph.add_node("curate_question", curate_question)
graph.add_node("prompt_query_context", prompt_query_context)
graph.add_node("generate_sql", generate_sql)
graph.add_node("is_safe_sql", is_safe_sql)
graph.add_node("execute_sql", execute_sql)
graph.add_node("canceled_sql", canceled_sql)
graph.add_node("represent_final_answer", represent_final_answer)

# Linear pipeline leading up to safety verification
graph.add_edge(START, "curate_question")
graph.add_edge("curate_question", "prompt_query_context")
graph.add_edge("prompt_query_context", "generate_sql")
graph.add_edge("generate_sql", "is_safe_sql")

# Conditional edge based on safety judge outcome
graph.add_conditional_edges(
    "is_safe_sql",
    is_safe_sql_edge,
    {
        "execute_sql": "execute_sql",
        "canceled_sql": "canceled_sql",
    }
)

# Post-execution paths to completion
graph.add_edge("execute_sql", "represent_final_answer")
graph.add_edge("represent_final_answer", END)
graph.add_edge("canceled_sql", END)

# Compile the SQL Analyst graph
sql_analyst = graph.compile()
