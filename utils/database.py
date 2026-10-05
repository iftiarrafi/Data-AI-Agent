import os
from contextlib import contextmanager
from typing import Optional, Dict, Any
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_default_db_config() -> Dict[str, Any]:
    """Retrieves PostgreSQL configuration from environment variables."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "data-agent"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }


class DatabaseUtil:
    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        self.db_config = db_config or get_default_db_config()

    def get_connection(self):
        """Creates and returns a new database connection."""
        return psycopg2.connect(**self.db_config)

    @contextmanager
    def get_cursor(self):
        """
        Context manager that yields a cursor and automatically handles
        commit, rollback, and closing the connection cleanly.
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def schema_details(self, schema_name: str = "public") -> str:
        """
        Inspects database schema and returns structured information including
        tables, column types, and sample data.
        """
        schema_info_context = f"Database schema: {schema_name}\n"
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema=%s ORDER BY table_name;",
                    (schema_name,)
                )
                tables = cursor.fetchall()
                if not tables:
                    return f"No tables found in schema '{schema_name}'."

                for table in tables:
                    table_name = table[0]
                    schema_info_context += f"\nTable: {table_name}\n"

                    cursor.execute(
                        "SELECT column_name, data_type FROM information_schema.columns "
                        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position;",
                        (schema_name, table_name)
                    )
                    columns = cursor.fetchall()
                    for col in columns:
                        schema_info_context += f"  Column: {col[0]}, Data Type: {col[1]}\n"

                    cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
                    sample_rows = cursor.fetchall()
                    schema_info_context += "  Sample Data:\n"
                    for row in sample_rows:
                        schema_info_context += f"    {row}\n"

            return schema_info_context
        except Exception as e:
            error_msg = f"Error retrieving schema details: {e}"
            print(error_msg)
            return error_msg

    def execute_query(self, query: str) -> str:
        """
        Executes a SQL query against the database and returns the result as a string.
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return f"Columns: {columns}\nRows ({len(rows)}): {rows}"
                return "Query executed successfully (no rows returned)."
        except Exception as e:
            error_msg = f"Error executing query: {e}"
            print(error_msg)
            return error_msg


if __name__ == "__main__":
    db_config = get_default_db_config()
    db = DatabaseUtil(db_config)
    details = db.schema_details("public")
    print(details[:500])