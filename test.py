import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
load_dotenv()

## Getting LLM

def get_llm(
    model_name: str = "openai/gpt-oss-120b",
    #model_name: str = "openai/gpt-oss-20b",
    #model_name: str = "qwen/qwen3.8-27b",
    #model_name: str = "openai/gpt-oss-safeguard-20b",
    temperature: float = 0.1,):
    api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
    )
    return llm

