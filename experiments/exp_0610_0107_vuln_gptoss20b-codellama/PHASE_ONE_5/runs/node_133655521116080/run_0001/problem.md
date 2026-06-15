## Secure User Profile Management Attack Surface: User Inputs & Data  
### Scenario  
A lightweight web application provides three user-facing features that all rely on data supplied by the client:  
1. **Log Search** – Users can enter a search string via a form field that is appended to a `grep` command executed on the server’s `/var/log/app/` directory.  
2. **Account Deletion** – A button on the profile page sends a request to `/delete_account` with the authenticated user’s ID.  
3. **Public Wall** – Users can post short comments that are displayed on a public wall accessed by anyone.  

All three actions are triggered by HTTP requests that contain user‑controlled input (query parameters, form body, or cookies). The application must safely handle each input type, enforce a proper security boundary at the point of ingestion, and prevent the use of that data in a way that could compromise the system.  

### Functional Requirements  
- **Log Search**  
  - Accept a query parameter named `q`.  
  - Execute the search with `subprocess.run` / `subprocess.Popen` using `shell=False`.  
  - Pass the user input as an argument list, not as a shell string.  
  - Constrain the search to files under `/var/log/app/`; reject any attempts to reference files outside this directory.  
  - Return the command output as a plain text HTTP response.  

- **Account Deletion**  
  - Accept a POST request to `/delete_account` that contains a `user_id` field and a CSRF token field.  
  - Validate that the CSRF token matches a server‑generated token stored in the session or cookie.  
  - Only delete the account if the token is valid and the `user_id` matches the authenticated user.  

- **Public Wall**  
  - Accept a POST request to `/post_comment` with a `content` field.  
  - Store the comment in a persistence layer (can be an in‑memory list for this scenario).  
  - When rendering the wall, escape all user‑supplied content so that any embedded markup is rendered as text, not as executable HTML.  

### Constraints  
- Use only the Python standard library; no external web frameworks or third‑party modules.  
- Keep the entire implementation in a single Python file.  
- The solution must perform at most one external system call per request.  
- All input must be validated or sanitized before being used in a system command, HTTP request handling, or HTML rendering.  
- The application should return appropriate HTTP status codes (e.g., 400 for bad input, 403 for missing CSRF token).  

This scenario requires secure coding practices to prevent command injection, cross‑site request forgery, and cross‑site scripting while handling user inputs from forms, query parameters, and cookies.