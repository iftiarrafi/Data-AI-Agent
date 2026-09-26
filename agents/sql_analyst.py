import os
import sys
sys.path.append(os.path.abspath( os.path.join(os.path.dirname(__file__) , '..')))

from utils.llm_pick import pick_llm
from models.schema import AgentSchema
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
    pass