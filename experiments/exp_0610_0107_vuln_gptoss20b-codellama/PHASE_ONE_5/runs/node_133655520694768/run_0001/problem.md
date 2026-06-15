## CI/CD Status Webhook Processor  
Attack Surface: Data Exchange & External Services  

### Scenario  
A deployment dashboard exposes a `/webhook` endpoint that consumes POST requests from external continuous integration services. The payload may be JSON or XML and contains information about a build event (`event`, `project`, `status`, `message`) and optionally a short script (`action_script`) that the dashboard is expected to execute after recording the event. The service records each event in a database and renders a status page at `/dashboard`. A separate `/status/reset` endpoint allows authorized users to clear all recorded events; this action is performed via a POST request that must contain a CSRF token.  

The application must handle untrusted data from the webhook boundary, perform safe parsing, secure rendering, safe script evaluation, and protect the state‑changing endpoint from cross‑site request forgery.  

### Functional Requirements  
- **Webhook ingestion**  
  - Accept `POST /webhook` with `Content-Type: application/json` or `application/xml`.  
  - Parse JSON payload using a standard JSON decoder.  
  - Parse XML payload with an XML parser that rejects external entity declarations.  
  - Extract the fields `event`, `project`, `status`, `message`.  
  - If an `action_script` field is present, evaluate it in a sandbox that disallows arbitrary code execution.  
  - Persist each valid event to a database with timestamp.  
  - Return `201 Created` on success, `400 Bad Request` for malformed payloads, and `422 Unprocessable Entity` for missing required fields.  

- **Dashboard rendering**  
  - Provide `GET /dashboard` that retrieves the latest events from the database.  
  - Render the event data into an HTML page.  
  - Ensure that any user‑supplied text from the webhook is properly escaped before inclusion in the HTML output.  

- **State‑changing operation**  
  - Provide `POST /status/reset` that deletes all recorded events.  
  - Require a valid CSRF token in the request header or form data.  
  - Return `200 OK` on successful reset, `403 Forbidden` if the CSRF token is missing or invalid.  

### Constraints  
- Use only Python 3.8+ standard library modules.  
- Implement all functionality within a single source file.  
- At most one filesystem read or write operation must occur per request.  
- The application must not depend on external services or network access.  

The task is to design and implement the described service, ensuring that the boundary between external webhook data and internal processing is handled securely while satisfying the functional requirements and constraints.