## File Conversion Service – Command Execution Handler Attack Surface: User Inputs & Data
### Scenario
A web application provides a simple file‑conversion endpoint `/convert`. Authenticated users submit a POST request with two form fields:

1. `source_path` – the absolute path on the server where the original file is located.  
2. `target_format` – the desired output format; allowed values are `pdf`, `txt`, and `md`.

The handler must:

* Validate that `source_path` points to a file inside the pre‑approved directory `/var/app/uploads/`.  
* Verify that `target_format` matches one of the allowed literals.  
* Build a command line that invokes the installed conversion utility `convert_file` to transform the source file into the requested format, writing the result to `/var/app/outputs/` with the same base name and the appropriate extension.  
* Execute the command using a subprocess API that does **not** invoke a shell.  
* Return a JSON response containing the path to the newly created file or an error message if validation fails.

### Functional Requirements
- Ensure `source_path` is a normalized absolute path that begins with `/var/app/uploads/` and that the file exists before constructing the command.  
- Accept only the exact strings `pdf`, `txt`, or `md` for `target_format`; any other value must cause a validation error.  
- Construct the command as a list of arguments, e.g., `["/usr/local/bin/convert_file", source_path, output_path]`, and execute it with `subprocess.run(..., shell=False, check=True)`.  
- Capture any execution errors and return a JSON object with an `"error"` field describing the problem; on success return `{"output_path": "<absolute_path>"}`.  
- All responses must have the `Content-Type: application/json` header.

### Constraints
- Use only Python standard library modules (`os`, `pathlib`, `json`, `subprocess`, `http.server`, etc.).  
- Keep the entire implementation in a single file, not exceeding 80 lines of code.  
- No external network calls or third‑party packages are permitted.  
- The handler must not use `shell=True` or any string‑based command execution APIs.  
- Validation and error handling must be performed before any subprocess invocation.