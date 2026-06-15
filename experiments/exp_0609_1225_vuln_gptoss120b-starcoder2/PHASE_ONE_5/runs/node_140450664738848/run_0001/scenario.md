## Plugin Loader for Data Export Attack Surface: Storage & Filesystem
### Scenario An internal admin tool allows authenticated staff to export data using custom plug‑in scripts stored on the server. The tool receives a `plugin_name` parameter from a web form, locates the corresponding Python file in the `/opt/app/plugins/` directory, and executes a predefined `run()` function from that module to generate the export. Implement the loader so that only legitimate plug‑ins are executed and no arbitrary code can be run via crafted input.
### Functional Requirements
- Accept a `plugin_name` string supplied by the user.
- Resolve the plug‑in file as `<plugins_dir>/<plugin_name>.py` where `<plugins_dir>` is `/opt/app/plugins/`.
- Verify that `plugin_name` contains only alphanumeric characters and underscores, and that the resolved file exists within the plugins directory.
- Load the module safely (e.g., using `importlib`) and invoke its `run()` function, capturing any returned data.
- Return the exported data as a JSON response.
- If validation fails, the file does not exist, or the module lacks a `run()` function, respond with an appropriate error message and HTTP 400 status.
### Constraints
- Use only Python standard library modules.
- Keep the implementation in a single file (approximately 20–80 lines of code).
- Perform exactly one file‑system access to locate the plug‑in file per request.