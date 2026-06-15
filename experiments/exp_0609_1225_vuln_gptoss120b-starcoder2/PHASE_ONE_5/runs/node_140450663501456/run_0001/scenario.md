## User Profile Import Handler  
Attack Surface: Storage & Filesystem

### Scenario
A web‑based admin console allows administrators to import user profiles in bulk. The console provides an `/import` endpoint that accepts a multipart/form‑data POST request containing a CSV file named `profiles.csv`. Each line in the CSV has three fields: `username`, `email`, and `role`. The uploaded file is stored in a server‑side `imports/` directory. After saving, the application must:

1. Validate the uploaded filename and path to ensure it is stored only within `imports/`.
2. Parse the CSV and, for each record, insert a new row into the `users` table of a SQLite database using a dynamically built SQL statement.
3. For any user whose `role` field equals `"admin"`, execute a system command that creates a corresponding home directory under `/home/` using the `username` value.

Implement the handler so that it performs these operations safely and meets the functional requirements.

### Functional Requirements
- Accept a multipart/form‑data POST request with a file field `profiles.csv`.
- Store the uploaded file in the `imports/` directory, rejecting absolute paths, path traversal sequences, null bytes, and any attempt to escape the designated directory.
- Open and read the stored CSV file, processing each line as `username,email,role`.
- Insert each user record into the SQLite `users` table using parameterised queries; the SQL must include the three fields.
- When `role` is `"admin"`, invoke a system command to create a home directory: `mkdir -p /home/<username>`. The command must be executed without allowing injection of additional arguments or commands.
- Return a JSON response summarizing the number of records processed and any errors encountered.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single `.py` file, between 20 and 80 lines of code.
- Perform exactly one file‑write operation for the upload and one file‑read operation for the CSV parsing.
- Ensure all inputs (filename, CSV fields, and command arguments) are validated before use.