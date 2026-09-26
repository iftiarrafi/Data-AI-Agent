import os
import sys
sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__) , '..')))

from utils.llm_pick import pick_llm
from models.schema import AgentSchema , JudgeSchema
from utils.database import DatabaseUtil
from langchain_core.messages import HumanMessage , AIMessage, SystemMessage, ToolMessage

# ------------- Agent Functions -------------

def curate_question(state:AgentSchema) -> AgentSchema :
    
    user_question = state.user_message
    
    llm = pick_llm("low")
    
    prompt = f"Curate the following question {user_question}"
    
    response = llm.invoke(prompt)
    
    state.curated_ques = response.content
    
    state.messages += [HumanMessage(content=f"{response.content}")]
    
    return state


def prompt_query_context(state: AgentSchema) -> AgentSchema:
    curate_question = state.curated_ques
    
    db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "data-agent"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    }
    
    obj = DatabaseUtil(db_config=db_config)
    
    schema_info = obj.schema_details("public")
    
    prompt = f"""
    L analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.  
    
    User's Original Query: {curate_question}

    Database Schema Details:
    {schema_info}
    
    """    
    state.prompt_query_context = prompt
    
    return state


def generate_sql(state: AgentSchema) ->AgentSchema:
    
    prompt = state.prompt_query_context
    
    llm = pick_llm("medium")
    
    result = llm.invoke(prompt).content
    
    state.generated_sql_query=result
    
    return state


def is_safe_sql(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query
    
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
    
    response = llm_judge.invoke(prompt).model_dump()
    state.is_safe = response['answer']
    state.comments = response['comments']
    
    return state