import os
import sys
import uuid
import ast
import pandas as pd
import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from graphs.data_agent_graph import data_agent
from graphs.sql_agent_graph import sql_analyst
from graphs.etl_agent_graph import etl_analyst
from utils.database import DatabaseUtil, get_default_db_config

# ==============================================================================
# 1. STREAMLIT PAGE CONFIGURATION & STYLES
# ==============================================================================
st.set_page_config(
    page_title="Multi-Agent SQL & ETL Studio",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Styling
st.markdown("""
<style>
    /* Global Typography & Font */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Hero Banner Header */
    .hero-container {
        background: linear-gradient(135deg, rgba(24, 32, 54, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 800;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        color: #94A3B8;
        font-size: 14.5px;
        line-height: 1.5;
        margin-bottom: 0px;
    }

    /* Badges & Chips */
    .chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12.5px;
        font-weight: 600;
        letter-spacing: 0.3px;
        margin-right: 8px;
    }
    .chip-sql {
        background: rgba(59, 130, 246, 0.15);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    .chip-etl {
        background: rgba(168, 85, 247, 0.15);
        color: #C084FC;
        border: 1px solid rgba(168, 85, 247, 0.3);
    }
    .chip-safe {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .chip-blocked {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* Metric & Stats Cards */
    .stat-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 12px 16px;
        text-align: center;
    }
    .stat-number {
        font-size: 20px;
        font-weight: 700;
        color: #F8FAFC;
    }
    .stat-label {
        font-size: 11.5px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Step Pipeline Tracker */
    .step-box {
        background: rgba(15, 23, 42, 0.6);
        border-left: 3px solid #3B82F6;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
        font-size: 13.5px;
    }

    /* Custom Streamlit chat message spacing */
    .stChatMessage {
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# 2. SESSION STATE INITIALIZATION
# ==============================================================================
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = str(uuid.uuid4())[:8]

if "pending_prompt" not in st.session_state:
    st.session_state["pending_prompt"] = None


# ==============================================================================
# 3. HELPER FUNCTIONS
# ==============================================================================
@st.cache_resource(ttl=300)
def check_db_health():
    """Returns database connection status and available table counts."""
    config = get_default_db_config()
    try:
        db = DatabaseUtil(db_config=config)
        if not db.connection:
            return False, "Failed to connect to PostgreSQL", {}
        cur = db.connection.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = [t[0] for t in cur.fetchall()]
        
        table_counts = {}
        for tbl in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM public.{tbl};")
                count = cur.fetchone()[0]
                table_counts[tbl] = count
            except Exception:
                table_counts[tbl] = "N/A"
        cur.close()
        db.connection.close()
        return True, "Connected", table_counts
    except Exception as e:
        return False, str(e), {}


def parse_sql_result_to_dataframe(result_str):
    """Attempts to safely parse stringified SQL tuple results into a pandas DataFrame."""
    if not result_str or not isinstance(result_str, str):
        return None
    try:
        data = ast.literal_eval(result_str)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], (tuple, list)):
            df = pd.DataFrame(data)
            return df
        return None
    except Exception:
        return None


def render_assistant_metadata(extra):
    """Renders structured expanders for route, SQL generated, judge evaluation, and tools."""
    if not extra:
        return

    route = extra.get("route", "")
    curated_ques = extra.get("curated_ques")
    sql_query = extra.get("generated_sql_query")
    is_safe = extra.get("is_safe")
    comments = extra.get("comments")
    sql_result = extra.get("sql_query_execution_result")
    tool_info = extra.get("tool_info", [])

    # Route Badge & Header
    badge_html = ""
    if route == "sql":
        badge_html += '<span class="chip chip-sql">🗄️ Route: SQL Analyst</span>'
    elif route == "etl":
        badge_html += '<span class="chip chip-etl">⚡ Route: ETL Pipeline Engine</span>'

    if is_safe == "Yes":
        badge_html += '<span class="chip chip-safe">🛡️ Safe Query (Verified)</span>'
    elif is_safe == "No":
        badge_html += '<span class="chip chip-blocked">🛑 Query Blocked by Security Judge</span>'

    if badge_html:
        st.markdown(f'<div style="margin-bottom: 12px;">{badge_html}</div>', unsafe_allow_html=True)

    # SQL Pipeline Details Expander
    if sql_query:
        with st.expander("🔍 SQL Pipeline Execution Trace (Click to inspect)", expanded=False):
            if curated_ques:
                st.markdown("**1. Curated Question:**")
                st.info(curated_ques)

            st.markdown("**2. Generated PostgreSQL Query:**")
            st.code(sql_query, language="sql")

            st.markdown("**3. Security Guardrail Evaluation:**")
            if is_safe == "Yes":
                st.success(f"**Passed Security Checks:** {comments or 'Read-only SELECT query verified.'}")
            else:
                st.error(f"**Security Violation Blocked:** {comments or 'Unsafe statement detected.'}")

            if sql_result and is_safe == "Yes":
                st.markdown("**4. Raw Database Execution Output:**")
                df = parse_sql_result_to_dataframe(sql_result)
                if df is not None and not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.code(sql_result, language="text")

    # ETL Pipeline Tool Details Expander
    if tool_info:
        with st.expander("⚙️ ETL Tool Call & Transformation Trace", expanded=False):
            for idx, item in enumerate(tool_info):
                item_type = item.get("type", "")
                if item_type == "call":
                    tool_name = item.get("name", "Tool")
                    st.markdown(f"**Step {idx+1}: Tool Invocation `{tool_name}`**")
                    st.json(item.get("args", {}))
                elif item_type == "result":
                    st.markdown(f"**Step {idx+1}: Tool Execution Output:**")
                    st.text(item.get("content", ""))


# ==============================================================================
# 4. SIDEBAR - CONTROLS, DB EXPLORER, ARCHITECTURE
# ==============================================================================
with st.sidebar:
    st.markdown("### Multi-Agent Studio")
    st.caption("Autonomous SQL Analyst & ETL Pipeline")
    
    st.markdown("---")

    # 1. Routing Mode Selection
    st.markdown("#### Execution Mode")
    agent_mode = st.radio(
        "Select workflow:",
        options=[
            " Smart Router (Multi-Agent)",
            " SQL Analyst (Direct)",
            " ETL Engine (Direct)"
        ],
        help="Smart Router automatically classifies intent. Direct modes execute specialized sub-graphs directly."
    )

    st.markdown("---")

    # 2. Database Connection & Schema Health
    st.markdown("####  PostgreSQL Database")
    db_ok, db_status, table_counts = check_db_health()
    db_cfg = get_default_db_config()

    if db_ok:
        st.success(f" **Connected to `{db_cfg['database']}`**")
        st.caption(f"Host: `{db_cfg['host']}:{db_cfg['port']}` | Schema: `public`")

        with st.expander(" View Database Tables & Counts", expanded=False):
            col_a, col_b = st.columns(2)
            items = list(table_counts.items())
            for i, (tbl, cnt) in enumerate(items):
                col = col_a if i % 2 == 0 else col_b
                with col:
                    st.metric(label=tbl, value=cnt)

            st.markdown("---")
            selected_table = st.selectbox("Inspect table schema:", options=list(table_counts.keys()))
            if selected_table and st.button(f"Preview `{selected_table}` (Top 5)"):
                try:
                    db = DatabaseUtil(db_cfg)
                    cur = db.connection.cursor()
                    cur.execute(f"SELECT * FROM public.{selected_table} LIMIT 5;")
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]
                    preview_df = pd.DataFrame(rows, columns=col_names)
                    st.dataframe(preview_df, use_container_width=True)
                    cur.close()
                    db.connection.close()
                except Exception as ex:
                    st.error(f"Error previewing table: {ex}")
    else:
        st.error(f"🔴 **Database Offline**: {db_status}")
        st.caption("Ensure PostgreSQL is running and DB_HOST, DB_NAME in .env are correct.")

    st.markdown("---")

    # 3. ETL Data Explorer
    st.markdown("#### 📁 ETL Workspace Explorer")
    extract_dir = os.path.join(PROJECT_ROOT, "data", "extract")
    transform_dir = os.path.join(PROJECT_ROOT, "data", "transform")

    extracted_files = os.listdir(extract_dir) if os.path.exists(extract_dir) else []
    transformed_files = os.listdir(transform_dir) if os.path.exists(transform_dir) else []

    with st.expander(" Extracted & Transformed Files", expanded=False):
        st.markdown("**Extracted Data (`data/extract`):**")
        if extracted_files:
            for f in extracted_files:
                fpath = os.path.join(extract_dir, f)
                st.text(f" {f} ({os.path.getsize(fpath)} bytes)")
        else:
            st.caption("No files yet in `data/extract/`")

        st.markdown("**Transformed Data (`data/transform`):**")
        if transformed_files:
            for f in transformed_files:
                fpath = os.path.join(transform_dir, f)
                st.text(f" {f} ({os.path.getsize(fpath)} bytes)")
        else:
            st.caption("No files yet in `data/transform/`")

    st.markdown("---")

    # 4. Multi-Agent Architecture Diagrams
    with st.expander(" Multi-Agent Architecture", expanded=False):
        st.markdown("#### System Topology")
        agent_img = os.path.join(PROJECT_ROOT, "data_agent_graph.png")
        sql_img = os.path.join(PROJECT_ROOT, "images", "sql_analyst_graph.png")
        etl_img = os.path.join(PROJECT_ROOT, "etl_analyst_graph.png")

        if os.path.exists(agent_img):
            st.markdown("**Supervisor Router Graph:**")
            st.image(agent_img, use_container_width=True)
        if os.path.exists(sql_img):
            st.markdown("**SQL Analyst Pipeline:**")
            st.image(sql_img, use_container_width=True)
        if os.path.exists(etl_img):
            st.markdown("**ETL Analyst Tool Graph:**")
            st.image(etl_img, use_container_width=True)

    st.markdown("---")

    # 5. Session Management & Reset
    st.caption(f" Session Thread: `{st.session_state['thread_id']}`")
    col_reset1, col_reset2 = st.columns(2)
    with col_reset1:
        if st.button(" New Chat", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.session_state["thread_id"] = str(uuid.uuid4())[:8]
            st.rerun()
    with col_reset2:
        if st.button(" Clear", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.rerun()


# ==============================================================================
# 5. MAIN CONTENT AREA - HERO & QUICK PROMPT PILLS
# ==============================================================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">
        <span> Multi-Agent SQL Analyst & ETL Engine</span>
    </div>
    <div class="hero-subtitle">
        Autonomous enterprise assistant orchestrating <b>Text-to-SQL with Security Guardrails</b> 
        and <b>Dynamic ETL Extraction & Pandas Transformations</b> via LangGraph & Groq LLMs.
    </div>
</div>
""", unsafe_allow_html=True)

# Quick Starter Prompt Buttons
st.markdown("##### 💡 Suggested Questions & Workflows")
pcol1, pcol2, pcol3, pcol4 = st.columns(4)

with pcol1:
    if st.button("🚗 Which user rides most?", use_container_width=True):
        st.session_state["pending_prompt"] = "Which user rides the most?"
with pcol2:
    if st.button("📊 Top 3 cities by users", use_container_width=True):
        st.session_state["pending_prompt"] = "What are the top 3 cities with the most registered users?"
with pcol3:
    if st.button("🛑 Test Security Guardrail", use_container_width=True):
        st.session_state["pending_prompt"] = "Drop the users table from the database"
with pcol4:
    if st.button("🌐 Extract PokeAPI to CSV", use_container_width=True):
        st.session_state["pending_prompt"] = "Extract data from API endpoint 'https://pokeapi.co/api/v2/pokemon' and save to data/extract in csv format"


# ==============================================================================
# 6. RENDER CHAT HISTORY
# ==============================================================================
for msg in st.session_state["chat_messages"]:
    if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get("role") == "user"):
        content = msg.content if hasattr(msg, "content") else msg.get("content", "")
        with st.chat_message("user"):
            st.write(content)
            
    elif isinstance(msg, AIMessage) or (isinstance(msg, dict) and msg.get("role") == "assistant"):
        content = msg.content if hasattr(msg, "content") else msg.get("content", "")
        extra = getattr(msg, "additional_kwargs", {}) or (msg.get("additional_kwargs", {}) if isinstance(msg, dict) else {})
        
        with st.chat_message("assistant"):
            render_assistant_metadata(extra)
            st.markdown(content)


# ==============================================================================
# 7. CHAT INPUT & EXECUTION PIPELINE
# ==============================================================================
user_input = st.chat_input("Ask a SQL query or request an ETL task (e.g., fetch API, transform CSV)...")

# If user clicked a suggested prompt pill, use that prompt
if st.session_state["pending_prompt"]:
    user_input = st.session_state["pending_prompt"]
    st.session_state["pending_prompt"] = None

if user_input:
    # 1. Store and display user message
    user_msg = HumanMessage(content=user_input)
    st.session_state["chat_messages"].append(user_msg)

    with st.chat_message("user"):
        st.write(user_input)

    # 2. Execute selected agent mode
    with st.chat_message("assistant"):
        config = {
            "configurable": {
                "thread_id": st.session_state["thread_id"]
            }
        }

        try:
            with st.status(" Agents collaborating on your request...", expanded=True) as status_box:
                
                # --- MODE A: SMART ROUTER (MULTI-AGENT GRAPH) ---
                if "Smart Router" in agent_mode:
                    st.write(" Step 1: Supervisor Router analyzing request intent...")
                    
                    # Run supervisor graph
                    result = data_agent.invoke(
                        {"messages": [user_msg], "route_response": None},
                        config=config
                    )
                    
                    last_msg = result["messages"][-1] if result.get("messages") else None
                    if not last_msg:
                        raise ValueError("No response returned from data_agent.")

                    ai_content = last_msg.content
                    extra_data = getattr(last_msg, "additional_kwargs", {}) or {}
                    route_picked = extra_data.get("route", result.get("route_response", "unknown"))

                    if route_picked == "sql":
                        st.write(" Step 2: Routed to **SQL Analyst Pipeline**")
                        if extra_data.get("is_safe") == "No":
                            st.write("🛡️ Step 3: Security Judge flagged query as UNSAFE. Execution cancelled.")
                        else:
                            st.write("🛡️ Step 3: Query verified safe. Executed against PostgreSQL.")
                        st.write(" Step 4: Synthesized executive summary report.")
                    elif route_picked == "etl":
                        st.write(" Step 2: Routed to **ETL Pipeline Engine**")
                        st.write(" Step 3: Executed data extraction / transformation tool.")
                        st.write(" Step 4: Formatted operation confirmation.")
                        
                    status_box.update(label="✅ Request completed successfully!", state="complete", expanded=False)

                # --- MODE B: DEDICATED SQL ANALYST SUBGRAPH ---
                elif "SQL Analyst" in agent_mode:
                    st.write(" Step 1: Refining user question for SQL generation...")
                    st.write(" Step 2: Inspecting live PostgreSQL schema details...")
                    st.write(" Step 3: Generating SQL & Evaluating with Security Judge...")
                    
                    sql_res = sql_analyst.invoke({
                        "messages": [user_msg],
                        "user_message": user_input
                    })
                    
                    ai_content = sql_res.get("final_answer", "SQL analysis complete.")
                    extra_data = {
                        "route": "sql",
                        "curated_ques": sql_res.get("curated_ques"),
                        "generated_sql_query": sql_res.get("generated_sql_query"),
                        "is_safe": sql_res.get("is_safe"),
                        "comments": sql_res.get("comments"),
                        "sql_query_execution_result": sql_res.get("sql_query_execution_result")
                    }
                    status_box.update(label=" SQL Analysis complete!", state="complete", expanded=False)

                # --- MODE C: DEDICATED ETL PIPELINE ENGINE SUBGRAPH ---
                elif "ETL Engine" in agent_mode:
                    st.write(" Step 1: Inspecting ETL requirements and tool availability...")
                    st.write(" Step 2: Executing API extraction or Pandas transformation script...")
                    
                    etl_res = etl_analyst.invoke({"messages": [user_msg]})
                    etl_msgs = etl_res.get("messages", [])
                    
                    tool_info = []
                    ai_content = "ETL operation complete."
                    for m in etl_msgs:
                        if getattr(m, "tool_calls", None):
                            for tc in m.tool_calls:
                                tool_info.append({"type": "call", "name": tc.get("name"), "args": tc.get("args")})
                        elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                            ai_content = m.content

                    extra_data = {
                        "route": "etl",
                        "tool_info": tool_info
                    }
                    status_box.update(label=" ETL execution complete!", state="complete", expanded=False)

            # Render assistant message content & rich trace
            render_assistant_metadata(extra_data)
            st.markdown(ai_content)

            # Append complete AIMessage with metadata to history
            assistant_msg = AIMessage(content=ai_content, additional_kwargs=extra_data)
            st.session_state["chat_messages"].append(assistant_msg)

        except Exception as e:
            st.error(f" An error occurred during execution: {str(e)}")
            st.info("Tip: If this is an API rate limit or database connection issue, check your `.env` configuration.")