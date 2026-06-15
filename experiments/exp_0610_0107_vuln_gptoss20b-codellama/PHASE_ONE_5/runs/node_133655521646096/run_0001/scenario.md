## Container‑Based System Helper Service
Attack Surface: Execution Environment & Infrastructure

### Scenario
A lightweight HTTP service runs inside a container orchestrated by a cloud platform. The container receives several environment variables that determine where scripts can be executed, how the database is connected, and where imported configuration may be staged. The service exposes three endpoints:

| Endpoint        | Purpose                                 | Input                                                    |
|-----------------|----------------------------------------|----------------------------------------------------------|
| `/run‑script`   | Execute a maintenance shell script.    | Query parameter `name` – the script file name.           |
| `/db‑query`     | Retrieve data from a PostgreSQL database.| JSON body containing `sql` and a list of `params`.      |
| `/import‑config`| Load application configuration from XML.| XML document in the request body.                        |

The container is started with these environment variables:

- `SCRIPT_DIR` – Absolute path to the directory that contains allowed scripts.  
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` – Credentials for the PostgreSQL database.  
- `CONFIG_DIR` – Absolute path where temporary configuration files may be stored.

The service must resolve requested script paths safely, execute scripts without using a shell interpreter, run SQL statements using parameterized queries, and parse XML with a parser that rejects external entity references.

### Functional Requirements
- **/run‑script**
  - Accept a `name` query parameter.  
  - Resolve the script path relative to `SCRIPT_DIR`, rejecting absolute paths, parent‑directory traversal (`..`), null bytes, and any path that resolves outside `SCRIPT_DIR`.  
  - Execute the script via `subprocess.run` with `shell=False`.  
  - Capture and return the script’s stdout, stderr, and exit code as JSON.  

- **/db‑query**
  - Accept a JSON body with `sql` (the SQL statement) and `params` (list of parameters).  
  - Execute the statement against the PostgreSQL database using a parameterized API that does not allow arbitrary query construction.  
  - Return the result set as JSON.  
  - If the statement is not a `SELECT`, respond with an error.  

- **/import‑config**
  - Accept an XML payload in the request body.  
  - Parse the XML with `xml.etree.ElementTree`, configured to disable DTDs and external entity resolution.  
  - Extract configuration elements and insert them into the database using safe, parameterized statements.  
  - Return a success or failure message.  

- **Startup Validation**
  - Verify that all required environment variables (`SCRIPT_DIR`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `CONFIG_DIR`) are set and non‑empty.  
  - If any variable is missing or invalid, the service refuses to start.  

### Constraints
- Use only Python’s standard library modules.  
- All code must reside in a single `.py` file.  
- Perform at most one file‑read or file‑write operation per request.  
- Do not create temporary files on disk; use in‑memory streams where possible.  
- The service must run inside a container without requiring privileged host access.