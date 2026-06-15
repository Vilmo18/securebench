import json
import os
import pickle
from base64 import b64decode

def execute(request):
    # Parse the JSON request body
    data = json.loads(request.body)
    
    # Validate the target file path
    if not data["target_file"] or ".." in data["target_file"]:
        return {"error": "Invalid target file path"}
    
    # Decode and deserialize the payload
    try:
        payload = pickle.loads(b64decode(data["payload"]))
    except Exception as e:
        return {"error": f"Failed to deserialize payload: {e}"}
    
    # Validate the script string
    if "os." in data["script"] or "subprocess." in data["script"]:
        return {"error": "Disallowed import"}
    
    # Execute the validated script in a restricted namespace
    try:
        result = eval(data["script"], {"payload": payload})
    except Exception as e:
        return {"error": f"Script execution failed: {e}"}
    
    # Write the result to the target file
    with open(os.path.join("safe_dir", data["target_file"]), "w") as f:
        f.write(result)
    
    return {"success": True}