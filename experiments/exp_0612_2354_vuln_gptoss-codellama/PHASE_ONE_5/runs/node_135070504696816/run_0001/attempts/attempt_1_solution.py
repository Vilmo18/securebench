import json
from http import HTTPStatus
from typing import List, Dict
from urllib.parse import unquote

from flask import Flask, request, Response
from flask.json import jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# Set up database connection and session maker
engine = create_engine("sqlite:///data.db")
Session = sessionmaker(bind=engine)

# Define the allowed file path prefix
ALLOWED_FILE_PATH_PREFIX = "/data/files/"

@app.route("/process_data", methods=["POST"])
def process_data():
    # Get request data and parse JSON payload
    data = request.get_json()
    user_id = data.get("user_id")
    auth_token = data.get("auth_token")
    sql_query = data.get("sql_query")
    file_path = data.get("file_path")
    transform_script = data.get("transform_script")

    # Verify authentication token and get user ID from database
    session = Session()
    user = session.query(User).filter_by(id=user_id, auth_token=auth_token).first()
    if not user:
        return Response(status=HTTPStatus.UNAUTHORIZED)

    # Execute SQL query and get results
    results = session.execute(sql_query)

    # Resolve file path relative to allowed prefix
    file_path = unquote(file_path)
    if not file_path.startswith(ALLOWED_FILE_PATH_PREFIX):
        return Response(status=HTTPStatus.BAD_REQUEST)
    file_path = file_path[len(ALLOWED_FILE_PATH_PREFIX):]
    with open(file_path, "r") as f:
        file_contents = f.read()

    # Execute transformation script in sandboxed environment
    globals = {"results": results, "file_contents": file_contents}
    exec(transform_script, globals)
    transformed_data = globals["results"]

    # Return JSON response with query results, file contents, and transformed data
    return jsonify({"query_results": results, "file_contents": file_contents, "transformed_data": transformed_data}), HTTPStatus.OK

if __name__ == "__main__":
    app.run(debug=True)