import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langgraph.prebuilt import ToolNode, tools_condition
from agents.etl_analyst import llm_node ,tools
from models.schema import ETLAgentState
from langgraph.graph import StateGraph, START, END

etl_analyst_graph = StateGraph(ETLAgentState)

etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tools", ToolNode(tools))

etl_analyst_graph.add_edge(START, "llm_node")


etl_analyst_graph.add_conditional_edges(
    "llm_node",
    tools_condition,
    {
        "tools": "tools",
        "__end__": END
    }
)

etl_analyst_graph.add_edge("tools", "llm_node")

etl_analyst = etl_analyst_graph.compile()
