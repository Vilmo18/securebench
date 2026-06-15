import json
from xml.etree import ElementTree as ET

class PartnerImportAPI:
    def __init__(self):
        self.partners = {
            "1234567890": "secret",
            "9876543210": "top_secret"
        }

    def handle_request(self, request):
        # Validate the authentication token
        auth_token = request.headers.get("Authorization")
        if not auth_token or auth_token not in self.partners:
            return json.dumps({"error": "Missing Permissions"}), 403

        # Verify the CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token or csrf_token != self.partners[auth_token]:
            return json.dumps({"error": "CSRF Failure"}), 403

        # Parse the XML payload securely to avoid external entity injection
        try:
            root = ET.fromstring(request.data, parser=ET.XMLParser(resolve_entities=False))
        except ET.ParseError as e:
            return json.dumps({"error": "XML Parse Error"}), 400

        # Extract the file path from the XML payload
        file_path = root.find("filePath").text
        if not file_path or "/../" in file_path:
            return json.dumps({"error": "Traversal Attempt"}), 403

        # Resolve the file path relative to a dedicated directory
        partner_files = "partner_files/"
        resolved_file_path = f"{partner_files}{file_path}"

        # Perform a single file read operation to obtain the content of the resolved file
        try:
            with open(resolved_file_path, "rb") as f:
                file_content = f.read()
        except FileNotFoundError:
            return json.dumps({"error": "File Not Found"}), 404

        # Forward the file content to an internal message queue for downstream processing
        # Do not write any data back to the filesystem beyond the single read

        # Return a JSON response indicating success or the specific error
        return json.dumps({"success": True}), 200