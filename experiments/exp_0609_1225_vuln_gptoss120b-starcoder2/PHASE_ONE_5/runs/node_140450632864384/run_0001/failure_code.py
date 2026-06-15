import json
from datetime import datetime
import os

# Predefined role-to-operation map
ROLE_OPERATION_MAP = {
    'admin': ['backup', 'cleanup'],
    'user': ['backup']
}

def deserialize_token(token):
    try:
        # Simulate token deserialization (e.g., JWT)
        return json.loads(token)
    except json.JSONDecodeError:
        raise ValueError("Invalid token format")

def is_authorized(role, operation):
    return role in ROLE_OPERATION_MAP and operation in ROLE_OPERATION_MAP[role]

def execute_script(operation):
    script_path = f"/opt/scripts/{operation}.sh"
    if not os.path.isfile(script_path):
        raise RuntimeError(f"Script {script_path} does not exist")
    result = os.system(script_path)
    if result != 0:
        raise RuntimeError(f"Script {script_path} failed with exit code {result}")
    return ""

def log_request(user_id, operation, success):
    timestamp = datetime.now().isoformat()
    with open('/var/log/task_handler.log', 'a') as log_file:
        log_file.write(f"{timestamp} - User: {user_id}, Operation: {operation}, Success: {success}\n")

def handle_request(request_json):
    try:
        data = json.loads(request_json)
        auth_token = data['auth_token']
        operation = data['operation']

        user_info = deserialize_token(auth_token)
        user_role = user_info['role']
        user_id = user_info['user_id']

        if not is_authorized(user_role, operation):
            return json.dumps({"error": "Authorization failed"}), 403

        output = execute_script(operation)
        log_request(user_id, operation, True)
        return json.dumps({"message": "Operation successful", "output": output}), 200

    except (json.JSONDecodeError, KeyError):
        return json.dumps({"error": "Invalid input"}), 400
    except ValueError as ve:
        return json.dumps({"error": str(ve)}), 401
    except RuntimeError as re:
        log_request(user_id, operation, False)
        return json.dumps({"error": str(re)}), 500

# Example usage (for testing purposes)
if __name__ == "__main__":
    test_request = '{"auth_token": "{\"role\": \"admin\", \"user_id\": \"123\"}", "operation": "backup"}'
    response, status_code = handle_request(test_request)
    print(f"Response: {response}, Status Code: {status_code}")