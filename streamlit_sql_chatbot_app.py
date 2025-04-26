# streamlit_sql_chatbot_app.py
"""
A Streamlit chatbot that connects to a SQL database, validates the
user‑supplied configuration, then lets the user chat in natural language.
Each question is converted to SQL with Gemini via `text2sql.generate`,
executed against the live connection, and the results are streamed back
into the conversation.  The full chat history is retained in
`st.session_state` so the dialogue feels continuous.

Dependencies
------------
streamlit>=1.31
pandas
psycopg2‑binary  # only if you need Postgres
mysql‑connector‑python  # only if you need MySQL / MariaDB
sqlite3 (built‑in)
google‑genai  # required by text2sql.py

Files expected in the same folder
---------------------------------
connect_database.py   # supplied by the user
text2sql.py          # supplied by the user

Run the app
-----------
streamlit run streamlit_sql_chatbot_app.py
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from connect_database import (
    create_database_connection,
    get_db_schema_as_create_statements,
)
from text2sql import generate as nl_to_sql

# -------------------------------------------------------
# ----------  Streamlit page styling & helpers ----------
# -------------------------------------------------------

st.set_page_config(
    page_title="💬 SQL Chatbot",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject a tiny bit of CSS for a cleaner aesthetic
st.markdown(
    """
    <style>
        /* give the page a light padding and a pleasant font */
        body {font-family: "Segoe UI", sans-serif;}
        .stChatMessage {border-radius: 10px; padding: 0.5rem 1rem;}
        .stChatMessage.user {background: #F0F2F6;}
        .stChatMessage.assistant {background: #EEF8F2;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------
# ----------  Session‑state initialisation  -------------
# -------------------------------------------------------

def init_state() -> None:
    """Make sure every key we rely on exists in `st.session_state`."""
    defaults = {
        "connected": False,
        "connection": None,
        "db_type": None,
        "schema": None,
        "messages": [],  # list[dict(role, content)]
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# -------------------------------------------------------
# ----------  Connection  form  -------------------------
# -------------------------------------------------------

def connection_form() -> None:
    """Render the DB‑config form and attempt a connection when submitted."""

    st.subheader("1️⃣  Connect to your database")

    with st.form("config_form", clear_on_submit=False):
        col_left, col_right = st.columns(2)

        with col_left:
            db_type = st.selectbox("Database type", ["sqlite", "postgres", "mysql", "mariadb"])
            db_file_or_name = st.text_input(
                "Database / file",
                value="example.db" if db_type == "sqlite" else "",
                help="Full path for SQLite, DB name for server databases.",
            )
            host = st.text_input("Host", value="localhost")
            port = st.number_input(
                "Port",
                value=5432 if db_type == "postgres" else 3306,
                step=1,
                format="%d",
            )
        with col_right:
            user = st.text_input("User", value="root")
            password = st.text_input("Password", type="password")
            st.markdown("\n")  # little vertical space
            submitted = st.form_submit_button("🔌 Connect")

    if not submitted:
        return

    # Build a config dictionary compatible with `connect_database.py`
    cfg = {
        "type": db_type,
        "database": db_file_or_name,
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
    }

    with st.spinner("Connecting ..."):
        conn = create_database_connection(cfg)

    if conn is None:
        st.error("❌ Could not connect. Please double‑check your credentials.")
        return

    # Fetch and cache the DB schema so we can feed it to Gemini later
    with st.spinner("Reading schema ..."):
        schema_str = get_db_schema_as_create_statements(conn, db_type)

    if not schema_str:
        st.error("❌ Connected, but failed to obtain schema. Aborting.")
        conn.close()
        return

    # Success: persist details in the session and rerun so the chat UI shows
    st.session_state.connected = True
    st.session_state.connection = conn
    st.session_state.db_type = db_type
    st.session_state.schema = schema_str

    st.success("✅ Connected successfully!  Scroll down to chat …")
    st.rerun()# st.experimental_rerun()


# -------------------------------------------------------
# ----------  Chat helpers  -----------------------------
# -------------------------------------------------------

def display_message(role: str, content: str | pd.DataFrame):
    """Convenience wrapper around st.chat_message so we always style the same."""
    with st.chat_message(role):
        if isinstance(content, pd.DataFrame):
            st.dataframe(content, use_container_width=True)
        else:
            st.markdown(content)


def run_sql_safe(question: str) -> tuple[str | None, pd.DataFrame | None]:
    """Turn natural language into SQL, execute it, and return (sql, dataframe)."""

    # 1 — LLM → SQL
    sql_json = nl_to_sql(question, st.session_state.schema)

    sql = None
    if isinstance(sql_json, dict):
        # `text2sql` might return {"sql": "..."} or {"query": "..."}
        sql = sql_json.get("sql") or sql_json.get("query")

    if not sql:
        return None, None

    # 2 — Run the query and return a DataFrame
    try:
        cur = st.session_state.connection.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=cols)
        cur.close()
    except Exception as ex:  # pylint: disable=broad-except
        st.error(f"SQL execution failed: {ex}")
        return sql, None

    return sql, df


# -------------------------------------------------------
# ----------  Main  UI  ---------------------------------
# -------------------------------------------------------

st.title("💬 SQL Chatbot — talk to your data!")

if not st.session_state.connected:
    connection_form()
    st.stop()

# Sidebar with simple connection details and a disconnect button
st.sidebar.header("Current connection")
with st.sidebar.container():
    st.write(f"**Type:** {st.session_state.db_type}")
    st.write(f"**Schema tables:** {st.session_state.schema.count('CREATE TABLE')}")
    if st.sidebar.button("🔒 Disconnect"):
        try:
            st.session_state.connection.close()
        except Exception:  # pragma: no cover
            pass
        for k in ["connected", "connection", "db_type", "schema", "messages"]:
            st.session_state.pop(k, None)
        st.experimental_rerun()

# Display chat history
for m in st.session_state.messages:
    display_message(m["role"], m["content"])

# Chat input
user_prompt = st.chat_input("Ask a question about your database …")

if user_prompt:
    # Save user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    display_message("user", user_prompt)

    with st.spinner("Thinking …"):
        sql_txt, results_df = run_sql_safe(user_prompt)

    if sql_txt is None:
        reply = "❌ I couldn't generate a valid SQL query for that question."
        st.session_state.messages.append({"role": "assistant", "content": reply})
        display_message("assistant", reply)
    elif results_df is None or results_df.empty:
        reply = f"**Generated SQL**:\n```sql\n{sql_txt}\n```\n⛔ The query ran but returned no rows."
        st.session_state.messages.append({"role": "assistant", "content": reply})
        display_message("assistant", reply)
    else:
        reply = f"**Generated SQL**:\n```sql\n{sql_txt}\n```"
        st.session_state.messages.append({"role": "assistant", "content": reply})
        display_message("assistant", reply)
        display_message("assistant", results_df)

# Tiny footer
st.caption("Built with ❤️ and Streamlit · v1.0")
