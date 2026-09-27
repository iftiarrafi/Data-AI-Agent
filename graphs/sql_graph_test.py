import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from IPython.display import Image
from graphs.graph import sql_analyst

if __name__ == "__main__":
    
    image = Image(sql_analyst.get_graph().draw_mermaid_png())
    with open("images/sql_analyst_graph.png", "wb") as f:
        f.write(image.data)
    
    input_schema = {
        "messages": [],
        "user_message": "how many different types of vehicles do we have? ", 
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }
    
    response = sql_analyst.invoke(input_schema)
    
    print(response.get('generated_sql_query'))
    print("\n")
    print(response.get('final_answer'))
