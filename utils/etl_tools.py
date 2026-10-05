import os
import requests
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class ETLTools:
    def __init__(self):
        pass

    def extract_load(self, url: str, output_folder: str, format: str) -> str:
        """
        Extracts data from a REST API endpoint and saves it to output_folder in the specified format.

        Args:
            url (str): The API endpoint.
            output_folder (str): The target directory to save the file.
            format (str): The file format ('csv', 'json', or 'parquet').

        Returns:
            str: Status message detailing the outcome.
        """
        try:
            target_folder = output_folder
            if not os.path.isabs(target_folder):
                target_folder = os.path.abspath(os.path.join(PROJECT_ROOT, output_folder))
            os.makedirs(target_folder, exist_ok=True)

            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            fmt = format.lower().strip().lstrip(".")
            filename = os.path.join(target_folder, f"extracted_data.{fmt}")

            # Normalize JSON response data
            if isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list):
                    items = data["results"]
                else:
                    items = data
            elif isinstance(data, list):
                items = data
            else:
                items = [data]

            df = pd.json_normalize(items)

            if fmt == "csv":
                df.to_csv(filename, index=False)
            elif fmt == "json":
                df.to_json(filename, orient="records", lines=True)
            elif fmt == "parquet":
                df.to_parquet(filename, index=False)
            else:
                return f"Unsupported format '{format}'. Supported formats: csv, json, parquet."

            return f"Data successfully extracted ({len(df)} records) and saved to: {filename}"
        except requests.exceptions.RequestException as e:
            return f"Failed to fetch data from API: {e}"
        except Exception as e:
            return f"Failed to extract and load data: {e}"

    def transform_load_context(self, file_path: str) -> str:
        """
        Inspects the file and returns summary/sample rows to guide LLM code generation.

        Args:
            file_path (str): Path to data file.

        Returns:
            str: Data context summary.
        """
        try:
            target_file = file_path
            if not os.path.isabs(target_file):
                abs_path = os.path.abspath(os.path.join(PROJECT_ROOT, file_path))
                if os.path.exists(abs_path):
                    target_file = abs_path

            if not os.path.exists(target_file):
                return f"File does not exist: {file_path}"

            file_extension = os.path.splitext(target_file)[1].lower()
            if file_extension == ".csv":
                df = pd.read_csv(target_file)
            elif file_extension == ".json":
                df = pd.read_json(target_file, lines=True)
            elif file_extension == ".parquet":
                df = pd.read_parquet(target_file)
            else:
                return f"Unsupported file format: {file_extension}"

            return (
                f"DataFrame shape: {df.shape}\n"
                f"Columns: {list(df.columns)}\n"
                f"Top 3 rows:\n{df.head(3).to_string()}"
            )
        except Exception as e:
            return f"Error reading file context: {e}"

    def execute_code(self, code: str) -> str:
        """
        Executes pandas transformation code in a controlled namespace.

        Args:
            code (str): Python pandas code to execute.

        Returns:
            str: Status string.
        """
        try:
            local_scope = {"pd": pd, "os": os}
            exec(code, globals(), local_scope)
            return "Code executed successfully."
        except Exception as e:
            return f"Failed to execute code: {e}"
