## Secure Order Webhook Processor Attack Surface: Data Exchange & External Services  
### Scenario  
An e-commerce platform offers a `/order/webhook` endpoint for third‑party marketplaces to notify it of new orders. The endpoint receives a JSON payload via HTTP POST. The payload contains order details such as `order_id`, `customer`, `items`, and an optional `metadata` map. The platform must deserialize the JSON into Python objects, validate the data, and forward the order to an internal inventory service via an HTTP POST request to `/inventory/update`. The deserialization boundary is the webhook input; all further processing must use only the validated data.  
### Functional Requirements  
- Accept an HTTP POST request containing a JSON body at `/order/webhook`.  
- Parse the JSON payload using a safe, standard‑library deserializer (e.g., `json.loads`).  
- Validate that the top‑level object is a dictionary and that required keys (`order_id`, `customer`, `items`) are present.  
- Ensure `items` is a list of dictionaries each containing `sku`, `quantity`, and `price`.  
- Reject any payload that contains additional keys, unexpected data types, or attempts to inject non‑JSON objects.  
- Construct a new dictionary containing only the validated fields.  
- Send the validated data as a JSON body to the internal inventory service at `/inventory/update` using an HTTP POST request.  
- Return HTTP 200 with a success message upon successful forwarding; otherwise return an appropriate error code (e.g., 400 for bad request).  
### Constraints  
- Use only Python standard library modules.  
- The implementation must reside in a single `.py` file.  
- No external network access is required beyond the internal inventory endpoint.  
- Perform at most one JSON parsing operation per request.  
- Do not use any serialization formats other than JSON for incoming or outgoing data.  
- All untrusted data must be validated before any application logic or downstream service interaction.