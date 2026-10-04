import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agents.etl_analyst import llm_node ,tool_node
from models.schema import ETLAgentSchema
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

graph = StateGraph(ETLAgentSchema)

graph.add_node("llm_node" , llm_node)
graph.add_node("tool_node" , tool_node)

graph.add_edge(START , "llm_node")

# conditional router function
def is_tool_call(state:ETLAgentSchema):
    
    tool_calls = state.messages[-1].tool_calls
    
    if tool_calls:
        return "tool_calls_edge"
    else:
        return "end"

graph.add_conditional_edges(
    "llm_node",
    is_tool_call,
    {
        "tool_calls_edge" : "tool_node",
        "end" : END
    }
)

graph.add_edge("tool_node","llm_node")

etl_analyst = graph.compile()

if __name__ == "__main__":
    # Optional
    from IPython.display import display, Image
    img = Image(etl_analyst.get_graph().draw_mermaid_png())
    with open("etl_analyst_graph.png", "wb") as f:
        f.write(img.data)

    response = etl_analyst.invoke({
    "messages": [
        "I want to extract the data from the API endpoint "
        "'https://pokeapi.co/api/v2/pokemon' and save it to "
        "data/extracted folder in the csv format"
    ]
})