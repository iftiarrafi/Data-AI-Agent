from pydantic import BaseModel, Field
from typing import Annotated, Literal
from operator import add
import os
import sys
from IPython.display import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.sql_analyst import (
    curate_question,
    prompt_query_context,
    generate_sql,
    is_safe_sql,
    execute_sql,
    canceled_sql,
    represent_final_answer,
    is_safe_sql_edge
)
from models.schema import AgentSchema, JudgeSchema
from langgraph.graph import StateGraph, START, END


graph = StateGraph(AgentSchema)


graph.add_node("curate_question", curate_question)
graph.add_node("prompt_query_context", prompt_query_context)
graph.add_node("generate_sql", generate_sql)
graph.add_node("is_safe_sql", is_safe_sql)
graph.add_node("execute_sql", execute_sql)
graph.add_node("canceled_sql", canceled_sql)
graph.add_node("represent_final_answer", represent_final_answer)


graph.add_edge(START, "curate_question")
graph.add_edge("curate_question", "prompt_query_context")
graph.add_edge("prompt_query_context", "generate_sql")
graph.add_edge("generate_sql", "is_safe_sql")

graph.add_conditional_edges(
    "is_safe_sql",
    is_safe_sql_edge,
    {
        "execute_sql_edge": "execute_sql",
        "canceled_sql_edge": "canceled_sql",
    }
)

graph.add_edge("execute_sql", "represent_final_answer")
graph.add_edge("represent_final_answer", END)
graph.add_edge("canceled_sql", END)

sql_analyst = graph.compile()


# if __name__ == "__main__":
#     image = Image(sql_analyst.get_graph().draw_mermaid_png())
#     with open("sql_analyst_graph.png", "wb") as f:
#         f.write(image.data)
    
#     input_schema = {
#         "messages": [],
#         "user_message": "How many tables do we have in the db?", 
#         "curated_ques": "",
#         "prompt_query_context": "",
#         "generated_sql_query": "",
#         "is_safe": "No",
#         "comments": "",
#         "sql_query_execution_result": "",
#         "final_answer": ""
#     }
    
#     response = sql_analyst.invoke(input_schema)
    
#     print(response.get('messages'))
#     print("********************************")
#     print(response.get('generated_sql_query'))
#     print("********************************")
#     print(response.get('sql_query_execution_result'))
