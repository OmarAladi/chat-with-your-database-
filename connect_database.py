# pip install psycopg2 
# pip install mysql-connector-python
import sqlite3
import psycopg2
import mysql.connector
from typing import Dict, Any, Optional

def create_database_connection(config: Dict[str, Any]):
    """
    Creates and returns a database connection based on configuration.

    Args:
        config: A dictionary containing database connection parameters.
                Must include 'type' ('sqlite', 'postgres', 'mysql', 'mariadb').
                Other keys depend on the database type (e.g., 'database', 'host', 'port', 'user', 'password').

    Returns:
        A database connection object if successful, None otherwise.
    """
    db_type = config.get("type")
    conn = None
    try:
        if db_type == "sqlite":
            conn = sqlite3.connect(config["database"])
        elif db_type == "postgres":
            conn = psycopg2.connect(
                host=config["host"], port=config["port"], user=config["user"],
                password=config["password"], dbname=config["database"]
            )
        elif db_type in ["mysql", "mariadb"]:
            conn = mysql.connector.connect(
                host=config["host"], port=config["port"], user=config["user"],
                password=config["password"], database=config["database"]
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        print(f"Connected to {db_type} database successfully.")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def get_db_schema_as_create_statements(connection, db_type: str) -> Optional[str]:
    """
    Retrieves the schema of the connected database and formats it
    as a string containing CREATE TABLE statements.

    Args:
        connection: A connected database connection object.
        db_type: The type of the database ('sqlite', 'postgres', 'mysql', 'mariadb').

    Returns:
        A string representing the database schema as CREATE TABLE statements,
        or None if the connection is invalid or an error occurs.
    """
    if not connection or not connection.is_connected():
        print("Error: Invalid connection for schema extraction.")
        return None

    cursor = connection.cursor()
    schema_statements = []

    try:
        if db_type == "sqlite":
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                create_table_sql = f"CREATE TABLE {table_name} (\n"
                column_definitions = []
                for col in columns:
                    cid, name, type, notnull, dflt_value, pk = col
                    col_def = f"    {name} {type.upper()}"
                    if notnull:
                        col_def += " NOT NULL"
                    if dflt_value is not None:
                        # Simple default handling for SQLite
                        if isinstance(dflt_value, str):
                            col_def += f" DEFAULT '{dflt_value.replace("'", "''")}'" # Basic escaping
                        else:
                            col_def += f" DEFAULT {dflt_value}"
                    # PK constraint is often added separately or as part of column definition
                    # For simplicity, we'll add it as part of definition if pk=1
                    if pk:
                         col_def += " PRIMARY KEY" # Simplified: assuming single-column PK or handling here

                    column_definitions.append(col_def)

                # Note: SQLite PRAGMA doesn't give full CREATE TABLE syntax including separate PK constraints, FKs etc.
                # This is a reconstruction based on available info.

                create_table_sql += ",\n".join(column_definitions) + "\n);"
                schema_statements.append(create_table_sql)


        elif db_type == "postgres":
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type='BASE TABLE';
            """)
            tables = cursor.fetchall()
            for (table_name,) in tables:
                 cursor.execute("""
                     SELECT column_name, data_type, is_nullable, column_default
                     FROM information_schema.columns
                     WHERE table_schema = 'public' AND table_name = %s
                     ORDER BY ordinal_position;
                 """, (table_name,))
                 columns = cursor.fetchall()
                 create_table_sql = f"CREATE TABLE {table_name} (\n"
                 column_definitions = []
                 for col_name, data_type, is_nullable, column_default in columns:
                     col_def = f"    {col_name} {data_type.upper()}"
                     if is_nullable == 'NO':
                         col_def += " NOT NULL"
                     if column_default is not None:
                         # Simple default handling (needs refinement)
                         if isinstance(column_default, str):
                             col_def += f" DEFAULT '{column_default.replace("'", "''")}'" # Basic escaping
                         else:
                             col_def += f" DEFAULT {column_default}"
                     column_definitions.append(col_def)

                 # Note: information_schema in Postgres requires querying table_constraints and key_column_usage for full PK/FK details
                 # This basic version doesn't include separate constraint definitions.

                 create_table_sql += ",\n".join(column_definitions) + "\n);"
                 schema_statements.append(create_table_sql)


        elif db_type in ["mysql", "mariadb"]:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
            tables = [row[0] for row in cursor.fetchall()]

            for table_name in tables:
                cursor.execute(
                    """
                    SELECT
                        column_name,
                        column_type,
                        is_nullable,
                        column_key,
                        column_default,
                        extra
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,)
                )
                columns = cursor.fetchall()

                create_table_sql = f"CREATE TABLE {table_name} (\n"
                column_definitions = []

                for col in columns:
                    col_name, col_type, is_nullable, column_key, column_default, extra = col
                    col_definition = f"    {col_name} {col_type.upper()}"

                    if is_nullable == 'NO':
                        col_definition += " NOT NULL"

                    if column_default is not None:
                        # Simplified default handling
                        if isinstance(column_default, str):
                            col_definition += f" DEFAULT '{column_default.replace("'", "''")}'" # Basic escaping
                        else:
                            col_definition += f" DEFAULT {column_default}"

                    if extra == 'auto_increment':
                        col_definition += " AUTO_INCREMENT"

                    # Add PRIMARY KEY if applicable (assuming single column primary key for simplicity)
                    if column_key == 'PRI':
                        col_definition += " PRIMARY KEY"

                    column_definitions.append(col_definition)

                # Note: Composite primary keys or separately defined constraints require additional queries
                # and more complex formatting.

                create_table_sql += ",\n".join(column_definitions) + "\n);"
                schema_statements.append(create_table_sql)

        else:
             # This case should theoretically not be reached if create_database_connection validates type
             print(f"Warning: Schema extraction not fully implemented or supported for type: {db_type}")
             return None


        full_schema_string = "\n\n".join(schema_statements)
        print("Schema extracted successfully.")
        return full_schema_string

    except Exception as e:
        print(f"Error extracting schema: {e}")
        return None
    finally:
         # Ensure the cursor is closed, but NOT the connection
         if cursor:
             cursor.close()

def execute_sql_query(connection, sql_query: str) -> Optional[list]:
    """
    Executes a read-only SQL query using an existing connection and returns results.

    Args:
        connection: A connected database connection object.
        sql_query: The SQL query string to execute (intended for read operations like SELECT).

    Returns:
        A list of result rows if the query is successful and returns data,
        or None if the connection is invalid, an error occurs, or the query returns no data.
    """
    if not connection or not connection.is_connected():
        print("Error: Invalid connection for query execution.")
        return None

    cursor = connection.cursor()
    results = None
    try:
        print(f"Executing query: {sql_query}")
        cursor.execute(sql_query)

        # Assuming it's a SELECT query that returns results
        # Use fetchall() to get all rows
        results = cursor.fetchall()

        print("Query executed successfully.")
        # Return results (list of tuples)
        return results

    except Exception as e:
        # Catch specific database errors if needed for finer control
        print(f"Error executing query: {e}")
        return None
    finally:
         # Ensure the cursor is closed
         if cursor:
            cursor.close()

# --- Main Project Logic (Illustrative Example) ---
# if __name__ == "__main__":
#     # Database configuration
#     config = {
#         "type": "mysql", # or "sqlite", "postgres"
#         "host": "localhost",
#         "port": 3306,
#         "user": "root",
#         "password": "",
#         "database": "clothing_store" # Make sure this database exists
#     }

#     conn = None # Initialize connection variable

#     try:
#         # 1. Create the database connection
#         conn = create_database_connection(config)

#         if conn:
#             # 2. Get the database schema
#             # Make sure to pass the connection object and type
#             database_schema_string = get_db_schema_as_create_statements(conn, config["type"])

#             if database_schema_string:
#                 print("\n--- Extracted Database Schema (CREATE TABLE statements) ---")
#                 print(database_schema_string)
#                 print("--------------------------------------------------------")

#                 # 3. --- LLM Interaction Part ---
#                 # This is where you would use the schema_string and user question
#                 # to prompt your LLM to generate an SQL query.
#                 user_question = "Show me the names of all t-shirts."
#                 print(f"\nUser Question: {user_question}")

#                 # Replace with your actual LLM call
#                 # llm_generated_sql = call_your_llm_model(database_schema_string, user_question)

#                 # --- Example: Use a dummy generated SQL query ---
#                 # In a real project, this comes from your LLM
#                 llm_generated_sql = "SELECT name FROM TShirts LIMIT 10;" # Example query

#                 if llm_generated_sql:
#                     print(f"\nLLM Generated SQL Query: {llm_generated_sql}")
#                     # 4. Execute the generated SQL query using the SAME connection
#                     query_results = execute_sql_query(conn, llm_generated_sql)

#                     # 5. Display the results
#                     if query_results is not None:
#                         print("\n--- Query Results ---")
#                         if query_results: # Check if there are any rows
#                            # You might want to print headers too
#                            # headers = [desc[0] for desc in cursor.description] # Need cursor to get description
#                            # print(headers) # Need to modify execute_sql_query to return cursor or description
#                            for row in query_results:
#                                print(row)
#                         else:
#                             print("Query executed, but returned no rows.")
#                         print("---------------------")
#                     else:
#                          print("Failed to execute query or retrieve results.")
#                 else:
#                      print("LLM did not generate a valid SQL query.")
#             else:
#                  print("Failed to extract database schema.")

#     except Exception as e:
#         print(f"An error occurred in the main process: {e}")
#     finally:
#         # 6. Close the connection when done
#         if conn and conn.is_connected():
#             conn.close()
#             print("\nDatabase connection closed.")