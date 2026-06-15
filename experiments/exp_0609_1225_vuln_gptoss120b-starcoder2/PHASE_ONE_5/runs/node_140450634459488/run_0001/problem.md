## User Account Management API Attack Surface: Authentication & Access Control
### Scenario
A web service provides a `/login` endpoint that authenticates users based on a JSON payload containing `username` and `password`. After successful authentication, the service creates a session token and returns it to the client. The same endpoint optionally accepts an `profile_xml` field, allowing users to submit an XML document that defines UI preferences. The service must parse this XML, store the preferences, and later use a `report_type` query parameter to generate a summary report by invoking a system utility. Access to the report generation feature is restricted to users with the “admin” role.

### Functional Requirements
- Accept a POST request with a JSON body containing `username`, `password`, and optionally `profile_xml`.
- Validate that `username` and `password` are non‑empty strings and conform to expected character sets.
- Authenticate the credentials against the stored user database and issue a signed session token on success.
- If `profile_xml` is provided, parse the XML safely and extract the `<theme>` and `<layout>` elements for storage in the user’s profile.
- Provide a GET `/report` endpoint that requires a valid session token and a `report_type` query parameter.
- Verify that the requesting user’s role includes “admin” before generating the report.
- Generate the requested report by invoking the system command `generate_report --type <report_type>` and return its output to the caller.
- Return appropriate error responses for authentication failures, missing or malformed inputs, unauthorized access, and invalid report types.

### Constraints
- Use only Python standard library modules.
- Keep the entire implementation within a single file (≈20–80 lines of code).
- Perform exactly one XML parsing operation per login request and one command execution per report request.