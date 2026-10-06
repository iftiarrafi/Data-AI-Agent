from pydantic import BaseModel , Field
from typing import Annotated , Literal ,Sequence , Optional
from operator import add
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# use TypedDict for agent Schema and BaseModel for llm's structured output

class SQLAgentState(TypedDict):
    """
    State for the SQL Analyst graph.
    Uses LangGraph's add_messages reducer to track conversation flow.
    """
    messages: Annotated[Sequence[BaseMessage] , add_messages] 
    user_message: Optional[str]
    curated_ques: Optional[str]
    prompt_query_context: Optional[str]
    generated_sql_query: Optional[str]
    is_safe : Literal["Yes" , "No"]
    comments: Optional[str]
    sql_query_execution_result: Optional[str]
    final_answer: Optional[str]
    

class JudgeSchema(BaseModel):
    """Schema for evaluating SQL query safety."""
    answer: Literal["Yes" , "No"] = Field(..., description="Indicates if the generated SQL query is safe to execute or not")
    comments: str = Field(..., description="Additional comments or feedback from the judge regarding the SQL query")
    


class ETLAgentState(TypedDict):
    """
    State for the ETL Analyst graph.
    Uses LangGraph's add_messages reducer for tool-calling loop.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]


class DataAgentState(TypedDict):
    messages : Annotated[Sequence[BaseMessage],add_messages]
    route_response : Optional[Literal["sql" , "etl"]]

class RouterSchema(BaseModel):
    answer: Literal["sql","etl"] = Field(..., description="Indicates whether the user's question is related to SQL or ETL operations")
    comments: str = Field(default="", description="Additional comments or feedback regarding the classification of the user's question")

