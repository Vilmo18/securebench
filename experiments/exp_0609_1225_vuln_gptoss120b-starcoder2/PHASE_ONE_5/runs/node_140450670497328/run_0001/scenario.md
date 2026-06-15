## Configurable Task Runner Attack Surface: Execution Environment & Infrastructure
### Scenario
A cloud‑based automation service allows administrators to define simple background tasks via a JSON configuration string supplied through an environment variable `TASK_CONFIG`. The service reads this variable at startup, deserializes the JSON into a Python dictionary, and then executes a single OS command specified by the `command` field using the `subprocess.run` API. Implement the loader so that the configuration is safely parsed and the command execution respects the intended constraints.
### Functional Requirements
- Read the `TASK_CONFIG` environment variable at program start.
- Parse the variable content as JSON to obtain a dictionary.
- The dictionary must contain a string field `command` that represents the OS command to run (no arguments list).
- Execute the command with `subprocess.run`, capturing stdout and stderr.
- If the environment variable is missing, empty, or the JSON is malformed, terminate with a clear error message.
- Reject any configuration where the `command` field is not a plain string (e.g., contains objects, arrays, or executable code snippets).
- Log the executed command and its output to standard output.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file not exceeding 80 lines.
- Perform exactly one deserialization step and one subprocess execution per program run.