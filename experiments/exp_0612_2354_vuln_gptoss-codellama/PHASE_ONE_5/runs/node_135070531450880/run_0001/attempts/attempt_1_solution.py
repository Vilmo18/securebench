import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from flask import Flask, request, send_file
from flask_session import Session
from werkzeug.datastructures import FileStorage

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def validate_sql_query(query: str) -> bool:
    """Validate the SQL query to ensure it is safe and secure."""
    # Check if the query contains only a single command
    if len(query.split(";")) > 1:
        return False
    # Check if the query includes disallowed keywords
    for keyword in ["DROP", "DELETE", "UPDATE"]:
        if keyword in query.lower():
            return False
    # Check if the query contains null bytes or other disallowed constructs
    if any(char == "\x00" for char in query):
        return False
    return True

def execute_sql_query(query: str) -> List[Dict[str, Any]]:
    """Execute the SQL query against the database and return the result set."""
    with sqlite3.connect("database.db") as connection:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return [dict(zip([column[0] for column in cursor.description], row)) for row in results]

def execute_python_code(code: str) -> Optional[str]:
    """Execute the Python code in a sandboxed namespace and return the output."""
    # Create a new namespace with only the built-ins that are safe to use
    import builtins
    import sys
    import types
    from io import StringIO
    from contextlib import redirect_stdout

    namespace = {}
    for name in dir(builtins):
        if not name.startswith("_"):
            namespace[name] = getattr(builtins, name)
    namespace["print"] = print
    namespace["sys"] = sys
    namespace["types"] = types
    namespace["StringIO"] = StringIO
    namespace["redirect_stdout"] = redirect_stdout

    # Execute the code in the sandboxed namespace
    try:
        exec(code, namespace)
    except Exception as error:
        return f"Error: {error}"

    # Return the output of the code
    with redirect_stdout(StringIO()) as stdout:
        namespace["main"]()
        return stdout.getvalue().strip()

@app.route("/admin/execute", methods=["POST"])
def admin_execute():
    """Handle the POST request to execute a SQL query and Python code."""
    # Check if the user is an admin
    session = Session()
    if not session.get("user_role") == "admin":
        return "Forbidden", 403

    # Validate the SQL query
    sql_query = request.json.get("sql_query")
    if not validate_sql_query(sql_query):
        return "Invalid SQL query", 422

    # Execute the SQL query and get the result set
    results = execute_sql_query(sql_query)

    # Validate the Python code
    python_code = request.json.get("python_code")
    if not isinstance(python_code, str):
        return "Invalid Python code", 422
    if not all(char in string.printable for char in python_code):
        return "Invalid Python code", 422

    # Execute the Python code and get the output
    output = execute_python_code(python_code)

    # Validate the uploaded configuration file
    config_file = request.files.get("config_file")
    if not isinstance(config_file, FileStorage):
        return "Invalid configuration file", 422
    filename = secure_filename(config_file.filename)
    if filename == "" or filename.endswith(".py"):
        return "Invalid configuration file", 422

    # Store the uploaded configuration file under `configs/`
    config_path = os.path.join("configs/", filename)
    with open(config_path, "wb") as file:
        file.write(config_file.read())

    # Return the result set and output of the Python code
    return jsonify({"results": results, "output": output, "config_path": config_path})

if __name__ == "__main__":
    app.run(debug=True)