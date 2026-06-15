import json
from http import HTTPStatus
from typing import List, Optional
from urllib.parse import unquote

import jwt
from flask import Flask, request, send_file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

# Set up database connection and session maker
engine = create_engine("postgresql://user:password@host/database")
Session = sessionmaker(bind=engine)

# Define the allowed bearer tokens
allowed_tokens = ["token1", "token2"]

# Define the base directory for file downloads
base_dir = "/srv/partner/files"

@app.route("/partner/sync", methods=["POST"])
def partner_sync():
    # Verify the bearer token in the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header.split()[0] != "Bearer":
        return {"message": "Missing or invalid bearer token"}, HTTPStatus.UNAUTHORIZED
    token = auth_header.split()[1]
    if token not in allowed_tokens:
        return {"message": "Invalid bearer token"}, HTTPStatus.UNAUTHORIZED

    # Parse the request body as JSON
    try:
        data = json.loads(request.data)
    except ValueError:
        return {"message": "Malformed JSON in request body"}, HTTPStatus.BAD_REQUEST

    # Extract the task and SQL query from the request body
    task = data.get("task")
    sql = data.get("sql")
    params = data.get("params", [])

    # Check that the task is valid
    if task not in ["query", "download"]:
        return {"message": f"Invalid task {task}"}, HTTPStatus.BAD_REQUEST

    # Execute the SQL query or download the file, depending on the task
    if task == "query":
        # Confirm that the SQL query is a SELECT statement
        if not sql.lower().startswith("select"):
            return {"message": "SQL query must start with SELECT"}, HTTPStatus.BAD_REQUEST

        # Execute the query using a parameterized API to prevent injection
        session = Session()
        result = session.execute(sql, params)
        session.close()

        # Return the result set as JSON
        return {"data": [dict(row) for row in result]}
    else:
        # Resolve the requested file path relative to the base directory
        file_path = unquote(data["file"])
        resolved_path = f"{base_dir}/{file_path}"
        if not resolved_path.startswith(base_dir) or not os.path.exists(resolved_path):
            return {"message": "File does not exist"}, HTTPStatus.NOT_FOUND

        # Return the file contents as a binary response with the appropriate MIME type and Content-Disposition header
        mime_type, _ = mimetypes.guess_type(resolved_path)
        return send_file(resolved_path, mimetype=mime_type, attachment_filename=os.path.basename(resolved_path))

if __name__ == "__main__":
    app.run(debug=True)