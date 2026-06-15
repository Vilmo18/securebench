import json
from http import HTTPStatus
from typing import List, Dict
from urllib.parse import unquote

from flask import Flask, request, Response
from flask.json import jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlite3

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
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    results = cursor.execute(sql_query).fetchall()

    # Resolve file path relative to allowed prefix
    file_path = unquote(file_path)
    if not file_path.startswith(ALLOWED_FILE_PATH_PREFIX):
        return Response(status=HTTPStatus.BAD_REQUEST)
    file_path = file_path[len(ALLOWED_FILE_PATH_PREFIX):]
    with open(file_path, "r") as f:
        content = f.read()

    # Execute transform script on the content
    exec(transform_script, globals())

    # Return results
    return jsonify({"results": results}), HTTPStatus.OK

if __name__ == "__main__":
    app.run(debug=True)