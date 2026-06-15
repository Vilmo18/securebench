## Role‑Based Account Management Attack Surface: Authentication & Access Control
### Scenario
A web service provides an `/account/settings` endpoint for authenticated users. The client sends a session cookie named `auth_token` that contains a base64‑encoded, JSON‑style serialized object with the fields `user_id`, `role`, and `preferences`. The endpoint must deserialize this token, verify the contained `role` against the server‑side user database, and then allow the user to (1) download a role‑specific configuration file, and (2) request a system‑level operation such as generating a user‑specific report by invoking a helper script. Both actions are gated by the verified role. Implement the handler so that deserialization, file access, and command execution are performed safely.
### Functional Requirements
- Read the `auth_token` cookie from the incoming request.
- Decode the base64 value and deserialize the token into a Python object.
- Retrieve the user record from the server’s in‑memory user store using `user_id` and confirm that the `role` in the token matches the stored role.
- For a valid request, allow the user to:
  1. Download a configuration file located under the directory `configs/`. The file name is derived from the verified `role` (e.g., `admin.cfg`, `editor.cfg`). Ensure that only files within `configs/` can be accessed.
  2. Trigger a report generation by executing the script `gen_report.sh` with the `user_id` as an argument. The command must be constructed without allowing injection of additional shell constructs.
- Return the configuration file as a binary response with appropriate content‑type headers.
- Return a JSON response indicating success or failure of the report generation.
- If deserialization fails, the role does not match, or any validation step is unsuccessful, respond with an HTTP 403 status.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file, between 20 and 80 lines of code.
- Perform at most one file‑read operation and one command‑execution operation per request.
- Do not write any files to disk; all outputs are returned directly to the caller.