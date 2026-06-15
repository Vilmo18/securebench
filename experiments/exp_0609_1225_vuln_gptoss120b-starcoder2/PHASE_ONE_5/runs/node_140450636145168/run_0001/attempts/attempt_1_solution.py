import base64
import json
import logging
from xml.etree.ElementTree import XMLParser, fromstring

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed maintenance commands
ALLOWED_COMMANDS = {"sync", "cleanup"}

def safe_loads(data):
    """Safely deserialize a base64-encoded string."""
    try:
        decoded_data = base64.b64decode(data)
        return json.loads(decoded_data)
    except (base64.binascii.Error, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode or deserialize payload: {e}")

def validate_command(command):
    """Validate the command against an allow-list."""
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"Invalid command: {command}. Allowed commands are: {ALLOWED_COMMANDS}")

def parse_metadata_xml(metadata_xml):
    """Parse XML metadata safely."""
    class NoExternalEntityResolver(XMLParser):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.set_feature("http://xml.org/sax/features/external-general-entities", False)
            self.set_feature("http://xml.org/sax/features/external-parameter-entities", False)

    try:
        tree = fromstring(metadata_xml, parser=NoExternalEntityResolver())
        return {elem.tag: elem.text for elem in tree}
    except Exception as e:
        raise ValueError(f"Failed to parse metadata XML: {e}")

def handle_import(request):
    """Handle the import request."""
    try:
        payload = safe_loads(request["payload"])
        validate_command(request["command"])
        metadata = parse_metadata_xml(request["metadata_xml"])

        # Log extracted metadata fields
        for key, value in metadata.items():
            logger.info(f"Metadata {key}: {value}")

        return json.dumps({"status": "success", "message": "Import processed successfully."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

# Example request for testing
request = {
    "payload": base64.b64encode(json.dumps({"config": "example"}).encode()).decode(),
    "command": "sync",
    "metadata_xml": "<metadata><field1>value1</field1><field2>value2</field2></metadata>"
}

# Handle the example request
response = handle_import(request)
print(response)