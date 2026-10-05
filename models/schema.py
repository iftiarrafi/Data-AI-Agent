from typing import Annotated, Sequence, Optional, Literal
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# =====================================================================
# State Definitions for LangGraph (Using add_messages Reducer)
# =====================================================================

class SQLAgentState(TypedDict):
    """
    State for the SQL Analyst graph.
    Uses LangGraph's add_messages reducer to track conversation flow.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_message: Optional[str]
    curated_ques: Optional[str]
    prompt_query_context: Optional[str]
    generated_sql_query: Optional[str]
    is_safe: Optional[Literal["Yes", "No"]]
    comments: Optional[str]
    sql_query_execution_result: Optional[str]
    final_answer: Optional[str]


class ETLAgentState(TypedDict):
    """
    State for the ETL Analyst graph.
    Uses LangGraph's add_messages reducer for tool-calling loop.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]


class DataAgentState(TypedDict):
    """
    Top-level supervisor state for Data Agent.
    Routes queries to SQL or ETL sub-graphs and maintains conversation history.
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    route_response: Optional[Literal["sql", "etl"]]


# =====================================================================
# Backward Compatibility Aliases
# =====================================================================
AgentSchema = SQLAgentState
ETLAgentSchema = ETLAgentState
DataAgentSchema = DataAgentState


# =====================================================================
# Pydantic Schemas for Structured LLM Outputs
# =====================================================================

class JudgeSchema(BaseModel):
    """Schema for evaluating SQL query safety."""
    answer: Literal["Yes", "No"] = Field(
        ...,
        description="Indicates if the generated SQL query is safe (read-only) to execute or not"
    )
    comments: str = Field(
        ...,
        description="Detailed feedback or comments explaining the safety decision"
    )


class RouterSchema(BaseModel):
    """Schema for classifying user requests between SQL and ETL operations."""
    answer: Literal["sql", "etl"] = Field(
        ...,
        description="Indicates whether the user's request is related to SQL database querying or ETL operations"
    )
    comments: str = Field(
        default="",
        description="Additional reasoning regarding the routing decision"
    )