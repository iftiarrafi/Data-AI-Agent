import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


def pick_llm(level: str = "low"):
    """
    Picks the appropriate LLM based on task requirement.

    Args:
        level (str): The level of question/task ("low", "medium", or "high").

    Returns:
        ChatGroq: Configured ChatGroq instance.
    """
    api_key = os.getenv("GROQ_API_KEY")
    lvl = level.lower().strip()

    if lvl == "high":
        return ChatGroq(model="openai/gpt-oss-120b", api_key=api_key, temperature=0)
    elif lvl == "medium":
        return ChatGroq(model="qwen/qwen3.8-27b", api_key=api_key, temperature=0)
    elif lvl == "low":
        return ChatGroq(model="qwen/qwen3.8-27b", api_key=api_key, temperature=0)
    else:
        raise ValueError(f"Unsupported level: {level}")


if __name__ == "__main__":
    llm = pick_llm("low")
    print(llm.invoke("What is the capital of Bangladesh?").content)