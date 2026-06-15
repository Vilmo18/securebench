## Email Notification Webhook Attack Surface: Data Exchange & External Services
### Scenario
An external partner sends a JSON payload to the `/api/notify` endpoint of an internal microservice. The payload contains a `subject`, a `body`, a `format` that can be `"html"` or `"text"`, and an optional `transform_script` that the service will evaluate to modify the body before sending the email. The endpoint performs a state‑changing operation (sending an email) and must be protected against cross‑site request forgery by requiring a CSRF token in the `X-CSRF-Token` header.

### Functional Requirements
- Accept a POST request with JSON containing:
  - `subject` (string, required)
  - `body` (string, required)
  - `format` (string, required; must be `"html"` or `"text"`)
  - `transform_script` (string, optional)
- Verify the `X-CSRF-Token` header is present and valid; reject requests without it with a 403 response.
- Validate that `format` is `"html"` or `"text"`. Return a 400 response for any other value.
- If `transform_script` is provided, evaluate it in a restricted environment to produce a transformed body. Disallow imports and disallowed built‑ins.
- When `format` is `"html"`, escape any user‑supplied markup in the transformed body before inserting it into an HTML email template to prevent script execution when the email is viewed.
- Send the email using the transformed (or original) body and subject; return a 200 response on success.

### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file.
- Perform at most one network‑send sink (the email transmission) per request.