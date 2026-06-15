## Container Management Dashboard Attack Surface: Execution Environment & Infrastructure
### Scenario
A cloud operations team uses an internal Flask‑based dashboard to manage container deployments. An authenticated administrator can upload a JSON file describing a new service, specify an XML configuration snippet for the service, provide optional SQL filter criteria for selecting existing database records, and choose a startup command template. The application must process the uploaded data, store the service definition in a PostgreSQL database, validate the XML, and finally invoke a container runtime (`docker run`) with the assembled command. Implement the endpoint so that it correctly authorizes the user, safely parses and validates the inputs, and executes the container launch without exposing the execution environment to unsafe control flow or data injection.

### Functional Requirements
- Verify that the requesting user has the **administrator** role before any processing occurs.
- Accept a multipart form submission containing:
  1. `service_json` – a JSON file with service metadata (name, image, environment variables).
  2. `config_xml` – an XML fragment that may include optional `<env>` elements.
  3. `sql_filter` – a plain‑text string used to filter rows in the `service_templates` table.
  4. `cmd_template` – a string containing placeholders (`{image}`, `{env_vars}`) that will be substituted to form the final `docker run` command.
- Parse `service_json` safely, ensuring that no object deserialization is performed on untrusted data.
- Parse `config_xml` with external entity processing disabled and reject any document that references external DTDs or entities.
- Construct a parameterized SQL query using `sql_filter` as a **value** (not as part of the query text) to retrieve the matching template rows.
- Combine the selected template data with the JSON metadata to populate the placeholders in `cmd_template`. The substitution must not allow execution of arbitrary code or evaluation of expressions.
- Build the final command as a list of arguments and invoke it using `subprocess.run` with `shell=False`.
- Log the executed command and the initiating administrator’s identifier.
- Return a JSON response indicating success or detailed validation errors.

### Constraints
- Use only Python 3 standard library modules (e.g., `json`, `xml.etree.ElementTree`, `sqlite3`/`psycopg2`‑style parameter binding, `subprocess`).
- Keep the entire implementation in a single file, not exceeding 80 lines of code.
- Perform at most one database query and one subprocess execution per request.
- Do not read or write any files outside the application’s working directory.