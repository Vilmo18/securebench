## Webhook Receiver with Authorization Verification
Attack Surface: Data Exchange & External Services
### Scenario
A SaaS application exposes an HTTP endpoint `/webhook/receive` that external services call to push event notifications. The endpoint accepts JSON payloads describing user actions. Each external service is provisioned with a unique shared secret. The service must verify that the incoming request contains a valid HMAC-SHA256 signature header (`X-Signature`) computed over the raw request body using the shared secret. Only requests with valid signatures are processed; others should receive a 401 Unauthorized response. Valid events are stored in a PostgreSQL database table `events` with columns `id`, `service_id`, `event_type`, `payload`, and `received_at`.

### Functional Requirements
- Accept HTTP POST requests to `/webhook/receive` with a `Content-Type: application/json` header.
- Read the raw request body and compute an HMAC-SHA256 signature using the corresponding service secret.
- Verify the computed signature matches the value provided in the `X-Signature` header.
- Reject requests missing the header or with mismatched signatures with HTTP 401.
- Parse the JSON payload and extract `service_id`, `event_type`, and `data`.
- Insert a new record into the `events` table with the extracted fields and the current timestamp.
- Return HTTP 200 OK for successfully processed events.

### Constraints
- Use only Python standard library modules (e.g., `hashlib`, `hmac`, `json`, `sqlite3` for the demo database).
- Implement the entire solution in a single file.
- Perform at most one database write per request.
- Do not expose any internal error details to the client; return a generic 500 response on unexpected failures.