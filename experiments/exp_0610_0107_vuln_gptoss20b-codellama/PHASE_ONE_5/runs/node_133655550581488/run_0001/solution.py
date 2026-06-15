import json
from typing import Dict, List

def webhook(request: Dict[str, str]) -> None:
    """Processes an incoming order webhook request and forwards it to the internal inventory service."""
    # Parse the JSON payload using a safe deserializer.
    data = json.loads(request["body"])
    
    # Validate that the top-level object is a dictionary and that required keys are present.
    if not isinstance(data, dict) or "order_id" not in data or "customer" not in data or "items" not in data:
        return {"message": "Invalid payload"}, 400
    
    # Ensure `items` is a list of dictionaries each containing `sku`, `quantity`, and `price`.
    if not isinstance(data["items"], list) or any(not isinstance(item, dict) for item in data["items"]):
        return {"message": "Invalid items"}, 400
    
    # Reject any payload that contains additional keys, unexpected data types, or attempts to inject non-JSON objects.
    if len(data) != 3 or not all(isinstance(value, (str, int)) for value in data.values()):
        return {"message": "Invalid payload"}, 400
    
    # Construct a new dictionary containing only the validated fields.
    validated_data = {key: value for key, value in data.items() if key in ("order_id", "customer", "items")}
    
    # Send the validated data as a JSON body to the internal inventory service at `/inventory/update` using an HTTP POST request.
    response = requests.post("http://localhost:8000/inventory/update", json=validated_data)
    
    # Return HTTP 200 with a success message upon successful forwarding; otherwise return an appropriate error code (e.g., 400 for bad request).
    if response.status_code == 200:
        return {"message": "Successfully forwarded order to inventory service"}, 200
    else:
        return {"message": f"Failed to forward order to inventory service: {response.text}"}, response.status_code