import os
import sys
from typing import Literal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.data_analyst import router_node , sql_node , etl_node
from models.schema import DataAgentState
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage



data_agent_graph = StateGraph(DataAgentState)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")

def route_edge(state: DataAgentState) -> Literal["sql_node_edge", "etl_node_edge"]:
    route = state.get("route_response")
    if route == "sql":
        return "sql_node_edge"
    elif route == "etl":
        return "etl_node_edge"
    else:
        raise ValueError(f"Invalid route response: {route}")


data_agent_graph.add_conditional_edges("router_node", route_edge,
                                {
                                "sql_node_edge": "sql_node",
                                "etl_node_edge": "etl_node"
                                })
# Connect worker nodes to completion
data_agent_graph.add_edge("sql_node", END)
data_agent_graph.add_edge("etl_node", END)


data_agent = data_agent_graph.compile()

