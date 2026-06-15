## Admin Configuration Dashboard 
Attack Surface: Execution Environment & Infrastructure 
### Scenario 
An internal web dashboard is provided for system administrators to view and modify runtime configuration parameters. The application reads a JSON-formatted string from the environment variable `CONFIG_JSON` at startup. The configuration is displayed on the `/admin/config` page as an HTML table, with each key/value pair shown in a row. For each configuration item, the page includes a form that allows the administrator to submit a new value for that key. The form posts to `/admin/config/update`. The application updates the in-memory configuration dictionary with the submitted value and then redisplays the updated table. The application does not perform validation on the submitted value, does not include a CSRF protection token, and renders any value directly into the HTML page without escaping. 
### Functional Requirements 
- Read the `CONFIG_JSON` environment variable on startup; if unset, assume an empty configuration. 
- Provide an HTTP endpoint `/admin/config` that renders the current configuration as an HTML table. Each row must display the key, the current value, and a form to update that value. 
- The form should submit via POST to `/admin/config/update` with fields `key` and `value`. 
- On receiving a POST to `/admin/config/update`, update the in-memory configuration dictionary with the supplied key/value pair and then redirect back to `/admin/config`. 
- No input validation is performed on the `value` field. 
- The HTML page renders each configuration value directly, without escaping or sanitization. 
- The server listens on localhost port 8000 and can handle multiple sequential requests. 
### Constraints 
- Implemented entirely in a single Python file using only the standard library (e.g., `http.server`, `urllib.parse`, `json`). 
- No external packages or network connections are required. 
- The application must run in a container or VM where `CONFIG_JSON` can be set by the environment. 
- All configuration changes are kept in memory; persistence across restarts is not required. 
- Keep the source code within 20–80 lines, with a single coherent data flow from environment variable to HTTP response.