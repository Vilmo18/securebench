## Secure Content Submission and Notification API
Attack Surface: Data Exchange & External Services
### Scenario
A web application exposes two RESTful endpoints for client applications and third‑party services.  
1. `/api/submit` accepts a JSON payload containing a `title` and a `body` field from an authenticated user, stores the post, and later renders it on a public feed.  
2. `/api/notification/mark-read` marks a user notification as read; the endpoint expects a notification ID and is invoked by browser clients when the user clicks a “Mark as Read” button. The API is also called by external webhooks that update notification status. The service boundary is the JSON serialization between client and server.

### Functional Requirements
- **/api/submit**  
  - Accept a POST request with `Content‑Type: application/json`.  
  - Parse the JSON payload and extract `title` (string, max 200 characters) and `body` (string).  
  - Sanitize the `body` content to escape or remove characters that would be interpreted as HTML or script when rendered in a browser, ensuring it cannot be used for script injection.  
  - Store the sanitized `title` and `body` in the database.  
  - Respond with a JSON object containing the new post ID and a 201 status code.  
- **/api/notification/mark-read**  
  - Accept a POST request with a JSON body containing `notification_id` (integer).  
  - Require a CSRF protection token sent in a custom header (`X-CSRF-Token`) or as a request body field, and validate that the token matches the one stored in the user’s session.  
  - Verify that the notification exists and belongs to the authenticated user.  
  - Update the notification status to “read” in the database.  
  - Respond with a JSON object confirming the update and a 200 status code.  
- Both endpoints must validate the presence and type of required fields and return appropriate 400 or 401 responses on failure.

### Constraints
- Use only Python standard library modules.  
- The implementation must reside in a single Python file.  
- Do not perform external network calls or rely on third‑party services.  
- Store and manage CSRF tokens in the user’s session data.  
- Ensure that all JSON responses are correctly encoded and that no raw untrusted data is sent back to the client without proper sanitization.