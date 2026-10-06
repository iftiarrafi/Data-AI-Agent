import os
import sys
sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__) , '..')))

from utils.llm_pick import pick_llm
from models.schema import ETLAgentState
from utils.etl_tools import ETLTools
from langchain.tools import tool
from langchain_core.messages import HumanMessage , AIMessage, SystemMessage, ToolMessage

etl_tools = ETLTools()
# ETL Agents

# tools to be called

@tool
def extract_load_tool(url:str, output_folder:str, format:str) -> str:
    """
    Extracts data from a REST API endpoint (url) and saves it to output_folder
    in the requested format ('csv', 'json', or 'parquet').

    Args:
        url (str): The API endpoint to fetch data from.
        output_folder (str): The folder directory where data will be stored.
        format (str): The target format ('csv', 'json', or 'parquet').

    Returns:
        str: Outcome confirmation message.
    """
    
    return etl_tools.extract_load(url, output_folder, format)

@tool
def transform_load_tool(input_file_path:str , output_folder:str, output_format:str , user_question: str) -> str:
    """
    Transforms data from an existing file using pandas as requested by the user,
    and saves the output to output_folder.

    Args:
        input_file_path (str): Path to the source data file.
        output_folder (str): Destination folder for transformed file.
        output_format (str): Desired file format (e.g., csv, json, parquet).
        user_question (str): Instructions on what transformations to perform.

    Returns:
        str: Status message with execution summary.
    """
    
    sample_context = etl_tools.transform_load_context(input_file_path)
    llm = pick_llm("low")
    system_prompt = (
        "You are an expert Python Data Analyst who writes clean, executable Pandas code.\n"
        "Generate ONLY raw Python code to transform the data and save it to the specified destination.\n"
        "Rules:\n"
        "- Do NOT include any markdown formatting, backticks (no ```python or ```), or explanations.\n"
        "- The code must read the file into a DataFrame, apply necessary transformations as per the user's instructions, and save to the target location.\n"
        "- Use pandas functions directly (assume 'pd' is imported)."
    )
    user_payload = f"""
        Input File: {input_file_path}
        Destination Folder: {output_folder}
        Destination Format: {output_format}
        User Transformation Goal: {user_question}

        Data Context Preview:
        {sample_context}
    """
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_payload)
    ]).content
    
    pandas_code = response.strip().strip("`").lstrip('python').strip()
    
    execution_result = etl_tools.execute_code(pandas_code)

    return (
        f"Data transformed and saved at '{output_folder}' in '{output_format}' format.\n\n"
        f"Executed Pandas Code:\n{pandas_code}\n\n"
        f"Execution Status: {execution_result}"
    )



tools = [extract_load_tool , transform_load_tool]

llm = pick_llm("low")
llm_with_tools = llm.bind_tools(tools=tools)

ETL_SYSTEM_PROMPT = (
    "You are an expert ETL Data Analyst agent with access to data extraction and transformation tools.\n"
    "Your responsibilities:\n"
    "1. When the user requests to fetch or extract data from an API, call 'extract_load_tool'.\n"
    "2. When the user requests data transformation on an existing file, call 'transform_load_tool'.\n"
    "3. After tool execution finishes and you observe the tool result, formulate a helpful, concise summary of the operation for the user."
)
# nodes

def llm_node(state:ETLAgentState) -> dict:
    """
    Invokes the LLM with the full conversation history.
    Appends the resulting AIMessage (with or without tool_calls) to state via add_messages.
    """

    messages = state.get("messages", [])
    
    response = llm_with_tools.invoke(
        [SystemMessage(content=ETL_SYSTEM_PROMPT)] + list(messages)
    )

    return {
        "messages":[response]
    }


# def tool_node(state:ETLAgentState):
#     """
#     This node is responsible for invoking the appropriate tool based on the user's question and the context provided by the LLM.
#     """

#     tools_results = []

#     tools_by_name = {tool.name: tool for tool in tools}

#     tool_calls = state.messages[-1].tool_calls

#     for tool_call in tool_calls:

#         tool = tools_by_name[tool_call['name']]
#         observation = tool.invoke(tool_call['args'])

#         tools_results.append(ToolMessage(content=observation, tool_call_id = tool_call['id']))

#     final = [state.get("messages" , [])] + tools_results

#     return {
#         "messages" : final
#     }   
