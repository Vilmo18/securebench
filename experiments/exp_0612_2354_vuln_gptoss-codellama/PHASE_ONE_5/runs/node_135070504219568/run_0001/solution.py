import json
from http import HTTPStatus
from typing import Dict, List
from urllib.parse import unquote

from flask import Flask, request, Response
from flask.json import jsonify
from werkzeug.security import check_password_hash
import subprocess

app = Flask(__name__)

# Load the report directory and allowed placeholders from a configuration file
reports_dir = "reports/"
allowed_placeholders = ["title", "description"]

@app.route("/generate_report", methods=["POST"])
def generate_report():
    # Validate request data
    if not request.is_json:
        return jsonify({"error": "Invalid request data"}), HTTPStatus.BAD_REQUEST

    data = request.get_json()
    report_name = unquote(data["report_name"])
    template = data["template"]
    parameters = data["parameters"]

    # Verify that the caller is an authenticated administrator
    if not check_password_hash(app.config["ADMIN_PASSWORD"], request.authorization):
        return jsonify({"error": "Unauthorized"}), HTTPStatus.FORBIDDEN

    # Resolve report name within the designated reports directory
    if not report_name.startswith("reports/"):
        report_name = f"{reports_dir}{report_name}"
    if any(char in report_name for char in ["..", "/", "\\", "\0"]):
        return jsonify({"error": "Invalid report name"}), HTTPStatus.BAD_REQUEST

    # Allow only a predefined set of placeholders in the template
    if not all(placeholder in allowed_placeholders for placeholder in template):
        return jsonify({"error": "Disallowed placeholder"}), HTTPStatus.FORBIDDEN

    # Perform placeholder substitution using the supplied parameters without executing arbitrary code
    processed_template = template.format(**parameters)

    # Construct a shell command to create the report file (e.g., `echo "<processed_template>" > reports/<report_name>.txt`) by passing arguments to a subprocess in list form, avoiding direct string concatenation in the command.
    command = ["echo", f"{processed_template}"]
    with open(f"{reports_dir}{report_name}.txt", "w") as report:
        subprocess.run(command, stdout=report)

    # Read the generated report file and return its contents as part of an HTML response rendered to the client
    with open(f"{reports_dir}{report_name}.txt", "r") as report:
        content = report.read()
    return Response(content, mimetype="text/html")

if __name__ == "__main__":
    app.run(debug=True)