## Order Processing Webhook Handler  
Attack Surface: Data Exchange & External Services

### Scenario
A SaaS platform provides an HTTP endpoint `/api/v1/webhook/orders` that third‑party partners call to push new order information. The request body is a JSON document containing an `order_id`, a `customer` object, an `items` list, and an optional `metadata_xml` field. The service must:

1. Parse the incoming JSON.
2. Validate that required fields exist and conform to expected formats.
3. If `metadata_xml` is present, parse the XML to extract a `<priority>` element.
4. Store the order data in an in‑memory list.
5. Invoke a local reporting script by constructing a command line that includes the extracted priority value (if any) and the `order_id`.

Implement the handler so that untrusted data is safely processed at each step.

### Functional Requirements
- Accept HTTP `POST` requests with `Content-Type: application/json` at the `/api/v1/webhook/orders` endpoint.
- Parse the JSON payload using a safe deserialization method.
- Verify that `order_id` is a non‑empty string of alphanumeric characters, `customer.email` matches a basic email pattern, and each entry in `items` contains a positive integer `quantity` and a non‑empty string `sku`.
- If the optional `metadata_xml` field is present, parse it using an XML parser that disallows external entity resolution and only allows the expected `<priority>` element. The extracted priority must be one of the strings `low`, `medium`, or `high`; otherwise, reject the request.
- Append the validated order information (including the resolved priority, defaulting to `low` when not provided) to an in‑memory list called `order_store`.
- Build a command string to run the local script `generate_report.sh` with arguments `--order-id <order_id>` and `--priority <priority>`. Execute the command in a subprocess without invoking a shell.
- Return an HTTP 200 response with a JSON body `{ "status": "accepted", "order_id": "<order_id>" }` on success, or an appropriate 4xx error with a JSON error message on validation failure.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file, roughly 20–80 lines of code.
- Perform exactly one subprocess execution per request.
- Do not write any files to disk; all data must remain in memory.