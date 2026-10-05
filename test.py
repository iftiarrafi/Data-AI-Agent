import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()


def get_llm(
    model_name: str = "qwen/qwen3.8-27b",
    temperature: float = 0.0,
):
    """Factory function to instantiate a ChatGroq LLM instance."""
    api_key = os.getenv("GROQ_API_KEY")
    return ChatGroq(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
    )


if __name__ == "__main__":
    llm = get_llm()
    response = llm.invoke([HumanMessage(content="Hello! Verify LLM connectivity.")])
    print(response.content)
