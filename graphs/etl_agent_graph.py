import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from models.schema import ETLAgentState
from agents.etl_analyst import llm_node, tools

# Initialize StateGraph with ETLAgentState (using add_messages reducer)
etl_analyst_graph = StateGraph(ETLAgentState)

# Nodes: LLM reasoning node and LangGraph prebuilt ToolNode
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tools", ToolNode(tools))

# Edges
etl_analyst_graph.add_edge(START, "llm_node")

# Conditional edge: if tool calls are requested by LLM, route to 'tools', else finish at END
etl_analyst_graph.add_conditional_edges(
    "llm_node",
    tools_condition,
    {
        "tools": "tools",
        "__end__": END,
    }
)

# Route tool outputs back to LLM to produce the final user summary
etl_analyst_graph.add_edge("tools", "llm_node")

# Compile the ETL Analyst graph
etl_analyst = etl_analyst_graph.compile()
