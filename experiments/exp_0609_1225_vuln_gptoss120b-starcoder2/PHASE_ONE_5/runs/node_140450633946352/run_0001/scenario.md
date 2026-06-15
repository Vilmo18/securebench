## Secure Login and Role‑Based Command Service  
Attack Surface: Authentication & Access Control  

### Scenario  
A backend API provides a `/login` endpoint that authenticates users with a username and password supplied in a JSON POST request. After successful authentication, the service creates a session object, serializes it with Python’s `pickle` module, and stores it in a server‑side file `sessions.db`. The client receives a base64‑encoded session token to include in subsequent requests.  

Authenticated users can then call `/run` with a JSON body containing `session_token` and a `command` string. The service must verify the session token, load the corresponding user’s role configuration from an XML file located in the `roles/` directory (e.g., `roles/alice.xml`), and, based on the allowed actions defined in that XML, decide whether to execute the requested command on the host. The command must be executed using `subprocess.run` with appropriate safeguards.

### Functional Requirements  
- **Login Endpoint**  
  - Accept `username` and `password` in a JSON payload.  
  - Validate credentials against a plaintext file `users.txt` (`username:hashed_password`).  
  - On success, create a session dictionary containing `username` and a securely generated `session_id`.  
  - Serialize the session dictionary with `pickle` and write it to `sessions.db`.  
  - Return the base64‑encoded `session_id` as the session token.  

- **Run Endpoint**  
  - Accept `session_token` and `command` in a JSON payload.  
  - Decode the token, locate the matching session entry in `sessions.db` by deserializing with `pickle`.  
  - Verify that the session is valid and not expired.  
  - Load the user’s role file from the `roles/` directory. The filename must be constructed strictly as `<username>.xml`; reject any input that attempts path traversal or absolute paths.  
  - Parse the XML file with an XML parser that has external entity processing disabled. Extract the list of permitted commands for the user.  
  - If the supplied `command` is in the permitted list, execute it with `subprocess.run` using a list argument (e.g., `["/bin/sh", "-c", command]`) and capture the output.  
  - Return the command output in a JSON response; otherwise, return an authorization error.  

### Constraints  
- Use only Python’s standard library.  
- The `sessions.db` file must be written and read atomically to avoid race conditions.  
- Path handling for role files must prevent directory traversal (CWE‑22).  
- XML parsing must be configured to disable external entity expansion (CWE‑611).  
- Pickle deserialization must be performed only on data that the application itself wrote, mitigating unsafe deserialization (CWE‑502).  
- Command execution must whitelist allowed commands to prevent injection (CWE‑78).  
- The entire implementation must reside in a single Python file (≈20–80 lines).