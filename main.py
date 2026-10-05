from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from graphs.data_agent_graph import data_agent


response = data_agent.invoke(
        {"messages":[HumanMessage(content="I want to extract the data from the API endpoint 'https://pokeapi.co/api/v2/pokemon' and save it to data/extract folder in the csv folder")],
        "route_response": ""})
# response = data_agent.invoke(
#         {"messages":[HumanMessage(content="How many distinct cities where users live in the db")],
#         "route_response": ""})

print(response["messages"][-1].content)