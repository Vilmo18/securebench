import json
from pathlib import Path
from subprocess import run, PIPE
from typing import Dict, Optional

# Define the allowed actions and their corresponding system commands
ACTIONS = {
    "compress": ["gzip", "-c"],
    "analyze": ["wc", "-l"]
}

# Set up logging for audit purposes
import logging
logging.basicConfig(filename="webhook_processor.log", level=logging.INFO)
logger = logging.getLogger(__name__)

def process_request(data: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Process a webhook request and return the result as a JSON object."""
    # Validate the API key
    api_key = data.get("X-API-Key")
    if not api_key or api_key != "secret":
        logger.warning(f"Invalid API key: {api_key}")
        return {"status": "error", "output": "", "error": "Invalid API key"}
    
    # Deserialize the request body and extract the file path and action
    try:
        file_path = data["file_path"]
        action = data.get("action")
    except KeyError as e:
        logger.warning(f"Missing field in request body: {e}")
        return {"status": "error", "output": "", "error": f"Missing field: {e}"}
    
    # Validate the file path and ensure it resolves inside the allowed directory
    try:
        file_path = Path(file_path).resolve()
        if not file_path.is_relative_to("/var/data/"):
            logger.warning(f"Invalid file path: {file_path}")
            return {"status": "error", "output": "", "error": f"Invalid file path: {file_path}"}
    except ValueError as e:
        logger.warning(f"Invalid file path: {e}")
        return {"status": "error", "output": "", "error": f"Invalid file path: {e}"}
    
    # Validate the action and ensure it is in the allowed list of commands
    if action not in ACTIONS:
        logger.warning(f"Invalid action: {action}")
        return {"status": "error", "output": "", "error": f"Invalid action: {action}"}
    
    # Execute the chosen action and capture stdout and stderr
    try:
        result = run(ACTIONS[action] + [str(file_path)], shell=False, stdout=PIPE, stderr=PIPE)
        output = result.stdout.decode("utf-8")
        error = result.stderr.decode("utf-8")
    except Exception as e:
        logger.warning(f"Error executing action: {e}")
        return {"status": "error", "output": "", "error": f"Error executing action: {e}"}
    
    # Return the result as a JSON object
    return {"status": "ok", "output": output, "error": error}