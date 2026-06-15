## Preference Submission Endpoint Attack Surface: User Inputs & Data
### Scenario A web application provides a POST endpoint `/preferences` that accepts a JSON body with a single field `settings_blob`. The value is a base64‑encoded serialized Python object representing user preferences. The handler must decode, validate, and deserialize the object, then store the sanitized preferences in a server‑side JSON file keyed by the authenticated user’s ID. Implement the endpoint so that the deserialization process only accepts a safe, predefined data structure and rejects any other content before any file system write occurs.
### Functional Requirements
- Accept a JSON payload containing the key `settings_blob`.
- Decode the `settings_blob` from base64.
- Deserialize the resulting bytes using a restricted deserializer that permits only a dictionary with the exact string keys `theme` (value must be `"light"` or `"dark"`), `notifications` (boolean), and `language` (ISO‑639‑1 two‑letter code). Any other object type, additional keys, or malformed data must cause the request to be rejected.
- After successful validation, write the preferences to a file `user_prefs/<user_id>.json`, creating the `user_prefs/` directory if it does not exist. Ensure the file path is constructed safely and cannot be manipulated by the client.
- Return a JSON response with `status: "saved"` on success, or an error message indicating invalid input on failure.
### Constraints
- Use only Python standard library modules.
- All validation and the restricted deserialization must occur before any file system write.
- The entire implementation must reside in a single Python file and must not depend on external services or network access.