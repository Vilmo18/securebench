## Order Processing API with JSON Input and Webhook Notifications
Attack Surface: Data Exchange & External Services

### Scenario
A microservice exposes a `/api/orders/create` HTTP endpoint that accepts order data as a JSON payload from partner systems. The payload includes fields such as `order_id`, `customer_name`, `items`, and a `callback_url` where the partner wishes to receive a status notification. The service must parse the JSON, validate the data, store the order in an internal list, and then send a POST request to the supplied `callback_url` with a JSON body indicating the order status. The response from the partner’s webhook should be logged. All data received from the partner (including the `customer_name` and any other string fields) may be reflected in HTML‑based email templates that are sent to internal staff, so proper escaping is required. The service must also protect the order‑creation endpoint against cross‑site request forgery‑like attacks by requiring a custom `X-Auth-Token` header that matches a pre‑shared secret known to trusted partners.

### Functional Requirements
- Accept a POST request to `/api/orders/create` with a JSON body containing at least `order_id`, `customer_name`, `items` (list), and `callback_url`.
- Verify that the request includes an `X-Auth-Token` header whose value matches the configured shared secret; reject requests with missing or incorrect tokens.
- Parse the JSON payload safely and validate that all required fields are present and of the correct type.
- Store the order data in an in‑memory collection.
- Send a POST request to the provided `callback_url` with a JSON payload `{ "order_id": "...", "status": "received" }`.
- Log the HTTP response status code and body returned by the partner’s webhook.
- When generating an internal HTML email notification that includes `customer_name` and other order details, escape all untrusted strings to prevent injection into the HTML content.
- Return a JSON response to the caller indicating success or detailed validation errors.

### Constraints
- Implement the entire functionality in a single Python file using only the Python standard library (e.g., `http.server`, `json`, `urllib.request`, `html` for escaping).
- Do not perform any network calls beyond the single POST to the `callback_url`.
- Keep the source file between 30 and 80 lines of code.