## File Query Service Attack Surface: User Inputs & Data
### Scenario
A web‑based inventory system provides an endpoint `/api/item` that accepts a JSON POST payload containing two fields: `image_name` (the name of an image file stored on the server) and `category_filter` (a string used to filter items by category in the database). Implement the handler so that it safely loads the requested image from the `images/` directory and executes a parameterized query to retrieve matching inventory items. The service must reject malformed or dangerous inputs and return appropriate error responses.
### Functional Requirements
- Parse a JSON body with `image_name` and `category_filter` fields.
- Load the file `images/<image_name>` and return its contents as a base64‑encoded string in the response.
- Query the database table `items` for rows where `category` matches `category_filter` and include the result set in the response.
- Return a 400 error if either field is missing or fails validation.
- Return a 404 error if the requested image does not exist within the `images/` directory.
- Return a 200 response containing the base64‑encoded image data and the list of matching items when both operations succeed.
### Constraints
- Use only Python’s standard library and the `sqlite3` module for database access.
- The implementation must reside in a single Python file (≈20–80 lines).
- Perform exactly one file‑read operation and one database query per request.
- Validation must ensure `image_name` does not contain path‑traversal characters or absolute paths, and `category_filter` is used in a parameterized SQL statement.