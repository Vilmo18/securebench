## User-Defined Report Generator  
Attack Surface: Storage & Filesystem

### Scenario
A web‑based analytics portal allows authenticated analysts to create custom CSV reports. The analyst submits a JSON payload containing a `report_name` (used as the filename) and a list of column definitions. The service must store the definition as a JSON file under a dedicated `reports/` directory and later generate a Python script named `<report_name>_builder.py` that reads the stored definition and produces the CSV file on demand.

### Functional Requirements
- Accept a POST request with a JSON body containing:
  - `report_name`: string supplied by the analyst.
  - `columns`: array of objects, each with `header` and `type`.
- Validate that `report_name` contains only alphanumeric characters, hyphens, or underscores and is no longer than 30 characters.
- Store the received column definition as `reports/<report_name>.json`. Reject any request that would cause the file to be written outside the `reports/` directory.
- Generate a Python source file `reports/<report_name>_builder.py` that imports `json`, loads the stored definition, and writes a CSV file using the specified columns. The generated script must be created safely without executing any untrusted code.
- Return a success response containing the path to the generated script. Return an error response for any validation or storage failure.

### Constraints
- Use only the Python standard library.
- All file operations must be confined to the `reports/` directory.
- The implementation must reside in a single Python file and be no more than 80 lines long.