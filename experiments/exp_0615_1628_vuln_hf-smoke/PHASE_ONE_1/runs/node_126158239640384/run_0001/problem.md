## Config Value Retrieval API Attack Surface: Data Exchange & External Services
### Target CWE(s): CWE-20
### Scenario
A service exposes a `/api/config` GET endpoint that accepts a `key` query parameter from client applications. The parameter specifies the name of a configuration setting stored in a server‑side `config.json` file. The service reads the requested setting and returns its value as JSON. The API is intended for use by internal front‑end components and automated tooling over HTTP.

### Functional Requirements
- Accept a GET request to `/api/config` with a single query parameter `key`.
- Validate that `key` is one of the allowed configuration names: `"max_connections"`, `"timeout_seconds"`, `"log_level"`. If the key is not in the whitelist, respond with `400 Bad Request`.
- Load the `config.json` file located in the same directory as the service. Read only the value associated with the validated key.
- Return a `200 OK` response with `Content-Type: application/json` and a body `{"key":"<key>","value":<value>}` where `<value>` is the JSON value from the file. If the key is missing from the file, respond with `404 Not Found`.
- Do not expose the entire `config.json` file or other keys in any response.

### Constraints
- Use only Python’s standard library modules (e.g., `http.server`, `json`, `urllib.parse`, `os`).
- Keep the entire implementation in a single Python file, under 80 lines of code.
- Perform at most one file‑read operation per request.