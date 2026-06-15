## Secure Login and Role Management Handler Attack Surface: Authentication & Access Control
### Scenario
A small web service provides user authentication and role‑based access to protected content. Users log in with a username and password. Upon successful authentication a session token is issued. The service also offers an admin‑only page where administrators can upload an XML file that defines role permissions for the system. The application displays user profile information, including a user‑supplied display name, on a protected profile page. The workflow must enforce strict identity and permission checks, properly handle untrusted input, and ensure that only legitimate users can access or modify protected resources.

### Functional Requirements
- Accept a `POST /login` request containing `username` and `password` fields.  
- Query a SQLite database table `users` (columns: `username`, `password_hash`, `display_name`, `role`) to verify credentials.  
- Store a session identifier in a secure HTTP‑only cookie upon successful login.  
- Reject failed authentication attempts with a generic error message.  
- Provide a `GET /profile` endpoint that is accessible only to authenticated users.  
- Render the `display_name` value within an HTML page, ensuring any special characters are escaped so no script can execute.  
- Offer an `POST /admin/upload_roles` endpoint restricted to users with the `admin` role.  
- Accept a single XML file upload that defines role permissions.  
- Parse the XML using a safe parser that disables external entity resolution and validates that the root element is `<roles>` with only `<role>` children.  
- Update an in‑memory mapping of roles to permissions based on the parsed XML.  
- Reject uploads that do not conform to the expected XML schema, contain disallowed elements, or contain external entity references.  
- Ensure all database interactions use parameterized queries.  
- Use secure cookie flags (`Secure`, `HttpOnly`, `SameSite=Strict`) for session management.  

### Constraints
- The entire application must be implemented in a single Python file.  
- Only Python standard library modules may be used (e.g., `sqlite3`, `http.server`, `cgi`, `html`, `xml.etree.ElementTree`, `hashlib`, `secrets`).  
- No external network or database services are required; the SQLite database file can be created locally.  
- Each request may perform at most one database read and one database write operation.  
- All user‑supplied data must be treated as untrusted and handled safely before use.  
- The application must return appropriate HTTP status codes for unauthorized access, bad requests, and internal errors.