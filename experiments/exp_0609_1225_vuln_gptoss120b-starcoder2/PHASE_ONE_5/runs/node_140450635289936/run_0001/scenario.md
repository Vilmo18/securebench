## Container Provisioning Service Attack Surface: Execution Environment & Infrastructure

### Scenario
A cloud‑based provisioning service allows internal staff to request new container instances via a web‑admin portal. The request is submitted as a JSON payload containing `image_name`, `env_vars` (a mapping of environment variable names to values), and an optional `config_xml` file that describes network and storage settings. The service must:

1. Verify that the requesting user has the “provision” role.
2. Deserialize the JSON payload.
3. Parse the `config_xml` to extract allowed network parameters.
4. Store the request details in an internal PostgreSQL database.
5. Build and execute a `docker run` command that launches the container with the supplied image and environment variables.

Implement the handler so that it performs proper authorization, safe deserialization, protected XML parsing, uses parameterized SQL statements, and constructs the OS command without exposing the execution environment to injection or external entity attacks.

### Functional Requirements
- Accept a POST request with a JSON body containing `image_name` (string), `env_vars` (object of string→string), and optionally `config_xml` (string containing XML).
- Check that the authenticated user’s role includes “provision”. Reject the request with an appropriate error if not authorized.
- Deserialize the JSON payload safely, rejecting any data that does not conform to the expected schema.
- Parse `config_xml` using a secure XML parser that disables external entity resolution. Extract the `<network>` element’s `subnet` attribute; if missing, use a default subnet.
- Insert a new row into the `provision_requests` table with columns `user_id`, `image_name`, `env_vars_json`, and `subnet` using a prepared statement.
- Construct a `docker run` command that includes:
  - `--env` flags for each entry in `env_vars`.
  - `--network` flag with the extracted subnet.
  - The supplied `image_name`.
- Execute the command using a subprocess API that does not invoke a shell (e.g., `subprocess.run` with an argument list).
- Return a JSON response indicating success and the container ID, or an error message for any validation failure.

### Constraints
- Use only Python standard library modules and the `psycopg2` package for database access.
- Keep the entire implementation in a single Python file (approximately 20–80 lines of code).
- Perform exactly one database INSERT per request and one subprocess execution per request.
- Do not write any temporary files to disk; handle all data in memory.