## Containerized Job Launcher Attack Surface: Execution Environment & Infrastructure
### Scenario
An internal web service allows authenticated users to submit data-processing jobs that run inside pre‑configured Docker containers. A client sends a JSON payload specifying the job name, input parameters, and optional environment variables. The service must deserialize the payload, load an XML job descriptor, validate all inputs, enforce access control, and launch the job by executing an OS command inside the container. The launched command must be constrained to a specific directory, use only allowed environment variables, and never allow traversal or execution of arbitrary files.

### Functional Requirements
- Accept a POST request containing a JSON payload with the following fields:
  - `job_name` – string, name of the job to run.
  - `params` – dictionary of job‑specific parameters.
  - `env` – optional dictionary of environment variable key/value pairs to set for the job.
- Ensure the request is made by a user who has explicit permission to execute the specified `job_name`.
- Deserialize the JSON payload safely, guarding against malicious data structures that could trigger arbitrary code execution.
- Resolve the job’s executable script by combining a trusted base directory with `job_name`, rejecting absolute paths, parent‑directory traversal, and any path components that could escape the base directory.
- Load an XML configuration file located within the job’s directory. The XML must be parsed safely, preventing external entity resolution or other XML-based attacks.
- Construct a shell command that runs the job inside a Docker container, passing in the validated parameters and environment variables. The command must not allow the job to access host filesystem paths outside the container boundary.
- Execute the constructed command as a subprocess, capturing its output and exit status.
- Return a JSON response containing the job’s status, stdout, and stderr, with appropriate HTTP status codes for success or error conditions.

### Constraints
- Use only Python standard library modules; no third‑party packages are allowed.
- The implementation must reside in a single Python file.
- The service must not perform more than one subprocess call per request.
- All file system operations must be relative to a predefined, writable base directory that is not exposed outside the container.
- Environment variable names and values supplied by the client must be validated to contain only alphanumeric characters, underscores, and hyphens.