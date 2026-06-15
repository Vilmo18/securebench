## Admin Config Upload Handler Attack Surface: Authentication & Access Control
### Scenario
An internal web service exposes a `/admin/upload_config` endpoint that accepts an XML configuration file from authenticated users. The client must provide a valid JWT in the `Authorization` header. Only users with the `admin` role are permitted to upload configuration files that may contain a `<script>` element specifying server‑side code to be executed. The service must parse the XML safely, enforce role-based access control, and execute the script in a sandboxed environment without allowing arbitrary code execution or external entity processing.
### Functional Requirements
- Accept an HTTP POST request to `/admin/upload_config` with a JWT in the `Authorization` header.  
- Validate the JWT, verify that the user has the `admin` role; otherwise respond with 403.  
- Read the XML payload from the request body.  
- Parse the XML using a safe parser that rejects any external entity references.  
- Locate the optional `<script>` element; if present, extract its text content.  
- Execute the extracted script using a restricted evaluation context that disallows access to built‑ins, file system, and network resources.  
- Return a JSON response indicating success or failure, and any output produced by the script.  
- Log the upload event with user identity and timestamp.  
### Constraints
- All logic must reside in a single Python file.  
- Only standard library modules are permitted (e.g., `json`, `datetime`, `xml.etree.ElementTree`, `jwt`).  
- The XML parser must be configured to disallow external entity resolution.  
- The script execution context must have no access to the filesystem, network, or arbitrary Python modules.  
- No persistent storage is required beyond logging.  
- The implementation should handle malformed XML gracefully with a 400 response.