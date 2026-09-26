import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()

def pick_llm(level:str):
    """
    Picks the appropriate LLM based on the level of the question

    Args:
        level (str): The level of question, can be "low" , "medium" or "high"
    Returns:
        The LLM instances
    """
    if level.lower() == "high" :
        llm = ChatGroq(model="openai/gpt-oss-120b" ,api_key= os.getenv("GROQ_API_KEY") , temperature=0)
    elif level.lower() == "medium" :
        llm = ChatGroq(model="openai/gpt-oss-120b" ,api_key= os.getenv("GROQ_API_KEY") , temperature=0)
    elif level.lower() == "low" :
        llm = ChatGroq(model="qwen/qwen3.8-27b" ,api_key= os.getenv("GROQ_API_KEY") , temperature=0)
    else:
        raise ValueError(f"Unsupported level : {level}")
    
    return llm


if __name__ == "__main__":
    llm_obj = pick_llm("low")
    print(llm_obj.invoke("What is the capital of Bangladesh?"))