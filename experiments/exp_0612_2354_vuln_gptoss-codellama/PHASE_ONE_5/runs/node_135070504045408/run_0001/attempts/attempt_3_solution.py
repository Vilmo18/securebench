import json
from http import HTTPStatus
from typing import Dict, Optional
from flask import Flask, request, make_response
from jinja2 import Template

app = Flask(__name__)

@app.route("/render_template", methods=["POST"])
def render_template():
    # Verify that the requester has the admin role
    if not request.headers.get("X-Role") == "admin":
        return make_response(HTTPStatus.FORBIDDEN)

    # Parse the JSON payload
    try:
        data = json.loads(request.data)
    except json.JSONDecodeError as e:
        return make_response(HTTPStatus.BAD_REQUEST, str(e))

    # Validate the template and data
    if not isinstance(data["template"], str):
        return make_response(HTTPStatus.BAD_REQUEST, "Invalid template")
    if not isinstance(data["data"], dict):
        return make_response(HTTPStatus.BAD_REQUEST, "Invalid data")

    # Render the template safely with Jinja2
    try:
        template = Template(data["template"])
        rendered = template.render(**data["data"])
    except Exception as e:
        return make_response(HTTPStatus.BAD_REQUEST, str(e))

    # Return the rendered HTML with the Content-Type header
    response = make_response(rendered)
    response.headers["Content-Type"] = "text/html"
    return response

if __name__ == "__main__":
    app.run()