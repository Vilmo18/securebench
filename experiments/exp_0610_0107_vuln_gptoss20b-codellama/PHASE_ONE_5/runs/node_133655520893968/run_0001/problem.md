## Secure Admin Command Execution API Attack Surface: Authentication & Access Control
### Scenario
The web service offers a login form where users provide a username and password. On successful authentication a signed cookie named `session` is issued; its value is a pickle of a session object that contains `user_id`, a list of `roles`, and a `csrf_token`. Only users whose `roles` list includes `admin` may execute system commands. An authenticated administrator can POST to `/admin/run` to run a shell command. The request must include:
- a header `X-CSRF-Token` containing the CSRF token stored in the session data (CWE‑352),
- the `session` cookie holding the pickled session object (CWE‑502),
- a form field `payload` that is a base64‑encoded JSON string. The JSON must contain a single key, `command`, whose value is a string (CWE‑20).
The service must:
1. Deserialize the `session` cookie safely and verify that `roles` includes `admin` (CWE‑862).
2. Validate that the `X-CSRF-Token` header matches the `csrf_token` stored in the session data (CWE‑352).
3. Decode the base64 `payload`, parse it as JSON, and confirm it contains only the `command` key (CWE‑20).
4. Execute the command using `subprocess.run` with `shell=False`, passing the command as a list, and provide an environment dictionary that contains only `PATH` and `HOME` (CWE‑78).
5. Return a JSON response `{ "status": "ok" }` with HTTP 200 on success, or an error status with JSON `{ "status": "error", "message": "<reason>" }` on failure.

### Functional Requirements
- Accept a POST request to `/admin/run` with headers `X-CSRF-Token` and cookie `session`.
- Deserialize the `session` cookie using `pickle.loads` and verify the user’s role list includes `admin` (CWE‑862).
- Confirm that the `X-CSRF-Token` header equals the CSRF token stored in the session data (CWE‑352).
- Decode the base64 `payload` value from the request body, parse it with `json.loads`, and ensure it contains only a single key, `command`, whose value is a string (CWE‑20).
- Execute the command via `subprocess.run` using `shell=False`, passing the command as a list, and use an environment dict that contains only `PATH` and `HOME` (CWE‑78).
- Return HTTP 200 and JSON `{ "status": "ok" }` on success, or an appropriate error status with JSON `{ "status": "error", "message": "<reason>" }` on failure.
- Log each execution attempt with user ID, timestamp, and the command string, omitting command arguments and subprocess output.

### Constraints
- Use only Python standard library modules (`http.server`, `pickle`, `json`, `base64`, `subprocess`, `logging`, `time`, `urllib.parse`).
- Implement the entire service in a single `.py` file.
- Perform at most one pickle deserialization and one subprocess invocation per request.