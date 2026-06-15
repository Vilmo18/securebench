## Admin Report Execution API Attack Surface: Authentication & Access Control  
### Scenario  
A web service provides an admin‑only endpoint `/admin/run_report` that allows privileged users to generate custom reports. The endpoint accepts a JSON payload containing:  
- `config_path`: a relative path to an XML configuration file that will be parsed.  
- `query`: a SQL SELECT statement to run against a local SQLite database.  
- `process_script`: a Python code snippet that will be executed on the query result.  

A separate `/login` endpoint authenticates users by accepting `username` and `password`, verifies credentials against a stored hash, and returns a session token that includes the user’s role.  

The workflow is:  
1. A client calls `/login` with credentials, receiving a session token.  
2. The client calls `/admin/run_report` with the JSON payload and the session token in the `Authorization` header.  
3. The service validates the session token, checks that the attached role is `admin`, then processes the payload as described below.  

### Functional Requirements  
- `/login`  
  - Accept `username` and `password`.  
  - Verify the password against a salted hash stored in a local file.  
  - Return a JSON response containing a unique session token and the user’s role.  
- `/admin/run_report`  
  - Require a valid session token; reject missing or malformed tokens with a 401 response.  
  - Verify that the token’s role is `admin`; reject non‑admin requests with a 403 response.  
  - Resolve `config_path` relative to a configured `configs/` directory. Reject absolute paths, parent‑directory traversal, and null byte characters. Read the XML file with a parser that disables external entities.  
  - Execute the `query` against a local SQLite database using a parameterized statement.  
  - Execute the `process_script` in a sandboxed environment that prohibits access to dangerous built‑ins and system calls.  
  - Return the output of the `process_script` as a JSON payload.  

### Constraints  
- Use only Python 3 standard library modules.  
- All code must reside in a single file.  
- The system must perform at most one file‑read operation per request.  
- No external network or database services may be accessed.  

The implementation must ensure that authentication and authorization controls are enforced before any payload processing occurs.