## Batch Job Configuration Processor
Attack Surface: Storage & Filesystem

### Scenario
A web‑based admin console allows privileged users to upload a job‑definition file named `job.xml`. The file is stored in the server’s `uploads/` directory. Each uploaded XML file describes a batch job that the backend must execute: it contains a shell command to run, a SQL statement to query the internal database, and a target output directory where the command’s result should be written. Implement the processing routine that, upon receiving a request to run a specific job, loads the corresponding `job.xml` from `uploads/`, extracts the command, SQL query, and output path, validates all extracted values, and then executes the command and the query, writing any command output to the designated directory.

### Functional Requirements
- Accept a `job_id` identifier supplied by the admin user (e.g., via a POST field).  
- Resolve the XML file as `uploads/<job_id>.xml`.  
- Verify that the resolved path is strictly inside the `uploads/` directory and does not contain path‑traversal sequences, null bytes, or symbolic‑link indirections.  
- Parse the XML file using a safe parser that disables external entity resolution.  
- Extract three elements from the XML:  
  1. `<command>` – the shell command to execute.  
  2. `<sql>` – the SQL statement to run against the internal SQLite database.  
  3. `<outputDir>` – the directory where the command’s stdout should be saved.  
- Validate that the `<command>` consists only of allowed whitelisted binaries (e.g., `ls`, `cat`, `grep`) and contains no additional characters or arguments that could alter its intended behavior.  
- Validate that the `<sql>` statement is a single, parameter‑less `SELECT` query that references only permitted tables (`jobs`, `results`). Reject any statement that contains semicolons, comments, or data‑manipulation keywords.  
- Validate that `<outputDir>` is a relative path that resolves under the server’s `job_outputs/` directory, rejecting absolute paths, parent‑directory references, or paths that resolve outside this directory.  
- Execute the validated command using a subprocess call that does not invoke a shell.  
- Execute the validated SQL statement using a parameter‑less cursor execution against the SQLite database.  
- Capture the command’s stdout and write it to a file named `result.txt` inside the validated `<outputDir>`.  
- Return a success response indicating that the job completed and the result file location.

### Constraints
- Use only Python’s standard library (e.g., `os`, `pathlib`, `xml.etree.ElementTree`, `subprocess`, `sqlite3`).  
- Keep the implementation within a single Python file (≈20–80 lines).  
- Perform exactly one file read (the XML file) and one file write (the result file) per job execution.  
- Do not perform any network operations.  
- The solution must handle all required input validation, command restriction, XML entity safety, and SQL statement restrictions as described.