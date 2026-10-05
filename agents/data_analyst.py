import os
import sys
sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__) , '..')))

from graphs.sql_agent_graph import sql_analyst
from graphs.etl_agent_graph import etl_analyst
from utils.llm_pick import pick_llm
from models.schema import AgentSchema , JudgeSchema , RouterSchema , DataAgentSchema
from utils.database import DatabaseUtil
from langchain_core.messages import HumanMessage , AIMessage, SystemMessage, ToolMessage


llm = pick_llm("low")

llm_router = llm.with_structured_output(RouterSchema)


def router_node(state:DataAgentSchema):

    message = state.messages[-1].content

    route_response_dict = llm_router.invoke(message).model_dump()

    route_response = route_response_dict['answer']

    state.route_response = route_response

    return state

def etl_node(state:DataAgentSchema):

    message = state.messages[-1].content

    response = etl_analyst.invoke(
             {"messages":[HumanMessage(content=f"""
            {message}
    """)]}
        ) 
    state.messages = state.messages + [response]

    return state

def sql_node(state:DataAgentSchema):

    message = state.messages[-1].content

    input_schema = {
        "messages": [],
        "user_message": f"{message}",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    response = sql_analyst.invoke(input_schema)

    state.messages = state.messages + [response.get('final_answer')]

    return state