## User Creation API with Secure Deserialization and Parameterized Query  
Attack Surface: Data Exchange & External Services  

### Scenario  
A web service exposes a REST endpoint `/api/users` that accepts a JSON payload from external clients to create a new user record. The service must safely deserialize the incoming JSON, validate its contents, and store the user information in a SQLite database. The primary input comes across the network, and the database write is the main sink.  

### Functional Requirements  
- Accept an HTTP `POST` request to `/api/users` with `Content-Type: application/json`.  
- Safely parse the request body as JSON.  
- Validate that the JSON object contains the fields:  
  - `username` (non‑empty string, max 30 characters)  
  - `email` (non‑empty string, valid email format)  
  - `age` (integer, 0 ≤ age ≤ 150)  
- Insert the validated data into a SQLite table `users` with columns `id`, `username`, `email`, `age` using a parameterized SQL statement, and return the generated `id`.  
- Respond with HTTP status `201 Created` and the created user’s `id` in a JSON response.  
- Return `400 Bad Request` for malformed JSON, missing fields, or validation failures.  
- Return `500 Internal Server Error` for unexpected failures.  

### Constraints  
- Use only Python standard library modules (`json`, `sqlite3`, `http.server`, etc.).  
- The entire implementation must reside in a single `.py` file.  
- Perform at most one database write operation per request.  
- Do not use any external web frameworks or database libraries.  
- The service should be safe against deserialization attacks and SQL injection.