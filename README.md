# Fine-tuning Google Gemma 3B on Synthetic Text-to-SQL Dataset

![Invoice Upload](./images/system_graph.png)

## 📚 Overview

This project fine-tunes **Google's `gemma-3-1b-it` model** on the **GretelAI `synthetic_text_to_sql` dataset**.

- Fine-tuning Notebook: [Open in Colab](https://colab.research.google.com/drive/1mRYAVqm9VPc0rZ9TTKDpFi_falj_QB6_?usp=sharing)

Then we build a system to **chat in natural language with your database** using the fine-tuned model:
- Connects to your database
- Reads the database schema
- Translates natural language questions into SQL queries
- Executes the queries
- Displays the results immediately

---

## 🗈️ System Interface Example

![Invoice Upload](./images/Screenshot_1.png)

![Invoice Upload](./images/Screenshot_2.png)

---

## 🚀 How to Run

### 1. Requirements

Install the required packages:

```bash
pip install streamlit pandas psycopg2-binary mysql-connector-python google-genai json-repair
```

---

### 2. Files Structure

| File | Purpose |
|:----|:--------|
| `connect_database.py` | Connects to different databases and extracts schema |
| `text2sql.py` | Converts natural language to SQL using Gemini API |
| `streamlit_sql_chatbot_app.py` | Streamlit web app for user interaction |

---

### 3. Launch the Application

```bash
streamlit run streamlit_sql_chatbot_app.py
```

---

## ⚙️ How the System Works

1. **Connect to your database** via a simple form.
2. **Supported database types**:
   - SQLite
   - PostgreSQL
   - MySQL / MariaDB
3. **Ask your question** in natural language.
4. The app:
   - Extracts your **schema** automatically
   - Sends your question + schema to the **fine-tuned LLM**
   - Receives a **SQL query** back
   - Executes the SQL query directly on your database
   - Displays the **results** in real-time
5. **Chat history** is maintained for a continuous conversation experience.

---

## 🧹 Example Chatbot Screenshot

Here's a full interaction flow:

![System Usage Screenshot](./aea3a320-f6a5-44bb-a5e6-9a3d6d73eac4.png)

---

## 💬 Key Features

- 🔌 Simple database connection from UI
- 🤖 Natural language to SQL conversion using fine-tuned LLM
- ⚡ Fast and real-time SQL execution
- 💃 Supports multiple SQL databases (PostgreSQL, MySQL, SQLite)
- 🌟 Clean and modern chat interface
- 🧪 Smart schema extraction

---

## 📜 License

This project is released under the MIT License.

---

# ✨ Enjoy querying your database using only natural language! ✨

