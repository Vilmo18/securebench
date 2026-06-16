## Secure Web Portal with Admin Script Upload Attack Surface: Authentication & Access Control  
### Scenario  
A lightweight web portal provides user authentication via username/password and session cookies. After logging in, each user can view and edit their public profile page, which displays a user-provided “bio” field. The portal also offers an admin-only dashboard that allows administrators to upload custom Python snippets intended to customize the portal’s behavior; the uploaded snippets are dynamically executed on the server. Additionally, the portal includes a “Change Email” form that performs a sensitive state-changing action and relies on a CSRF protection token.  
### Functional Requirements  
- Implement a login route that authenticates credentials, establishes a session cookie, and records the user's role (either “user” or “admin”).  
- Render the user profile page by inserting the stored “bio” content into the HTML template; the content must be properly escaped so that any embedded scripts are not executed when the page is rendered.  
- Provide a “Change Email” form that requires a valid CSRF token; the token must be generated per session, stored server‑side, and verified on form submission.  
- Create an admin‑only dashboard that accepts a file upload of a Python snippet; the uploaded snippet must be stored in a designated “scripts/” directory and later executed with `exec` only when the user has the “admin” role.  
- Ensure that session cookies have the `HttpOnly` flag and are signed to prevent tampering.  
- Reject any attempts to upload non‑Python files or snippets containing disallowed constructs such as `import os` or `subprocess`.  
### Constraints  
- Use only Python standard library modules (e.g., `http.server`, `http.cookies`, `uuid`, `hashlib`).  
- Keep the implementation within one file and limit the total line count to between 20 and 80 lines.  
- Perform at most one file‑write or file‑read sink per request.  
- Do not use any external services or network access.  
- The application must correctly enforce role‑based access control on all protected routes.  
- The implementation should not rely on third‑party libraries for CSRF, XSS sanitization, or session handling.