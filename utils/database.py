import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

class DatabaseUtil:
    def __init__(self , db_config):
        self.db_config = db_config
        try:
            self.connection = psycopg2.connect(**db_config)
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            self.connection = None
    
    def schema_details(self , schema_name):
        schema_info_context = ""
        connection = self.connection
        cursor = connection.cursor()
        
        schema_info_context = f"Database name : {schema_name}"
        try:
            cursor.execute("SELECT table_name from information_schema.tables where table_schema=%s;" ,(schema_name,))
            table_list = cursor.fetchall()
            
            for table in table_list:
                table_name = table[0]
                schema_info_context = f"{schema_info_context}\nTable: {table_name}\n"
                
                cursor.execute("SELECT column_name, data_type from information_schema.columns where table_name = %s;" ,(table_name,))
                columns_list = cursor.fetchall()
                
                for column in columns_list :
                    column_name = column[0]
                    data_type = column[1]
                    
                    schema_info_context = f"{schema_info_context} Column : {column_name} , Data Type:{data_type}\n"
                
                cursor.execute(f"SELECT * from {schema_name}.{table_name} LIMIT 5;")
                sample_data = cursor.fetchall()
                schema_info_context = f"{schema_info_context} \n Sample Data:"
                for row in sample_data:
                    schema_info_context = f"{schema_info_context} \n {row}"
                    
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            if cursor : cursor.close()
            if connection : connection.close()
        return schema_info_context
    def execute_query(self , query):
        try:
            connection = self.connection
            cursor = connection.cursor()
            cursor.execute(query=query)
            result = cursor.fetchall()
            connection.commit()
            
            return str(result)
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            if cursor : cursor.close()
            if connection : connection.close()
    
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "data-agent"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}
obj = DatabaseUtil(db_config)

result = obj.schema_details("public")

with open("test_schema_details.txt" , "w") as f:
    f.write(result)