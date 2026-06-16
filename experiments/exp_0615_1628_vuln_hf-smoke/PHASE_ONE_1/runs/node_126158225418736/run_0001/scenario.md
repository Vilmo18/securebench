## Admin Configuration Manager Attack Surface: Execution Environment & Infrastructure  
### Scenario  
An internal web dashboard runs inside a container and allows privileged administrators to upload a pickled configuration file, view and modify key environment variables, and trigger harmless system commands. The application presents a single‑page dashboard that renders the current value of the `APP_MODE` environment variable and offers a form to upload configuration updates. The form submits to `/admin/update-config`, and a separate endpoint `/admin/uptime` runs the `uptime` command and displays its output. All interactions are protected by CSRF tokens.  

### Functional Requirements  
- **Dashboard Rendering** – Serve an HTML page at `/admin/dashboard` that displays the current `APP_MODE` environment variable and the output of `/admin/uptime`.  
- **Environment Variable Display** – Embed the `APP_MODE` value into the HTML template after escaping it to prevent XSS.  
- **Configuration Upload** – Accept a POST request to `/admin/update-config` containing a file upload of a pickled object. Deserialize the payload safely, allowing only instances of a `Config` class that defines a `settings` dictionary. Update the environment variables with the key/value pairs from `settings`.  
- **CSRF Protection** – Require a valid CSRF token on all POST requests; reject requests without a token or with an invalid token.  
- **System Command Execution** – The `/admin/uptime` endpoint executes the `uptime` shell command via a subprocess, escapes the output, and returns it embedded in a safe HTML response.  
- **File Handling** – Store any uploaded configuration files in a dedicated `config/` directory and read/write them using a single file‑I/O operation per request.  

### Constraints  
- Implement the entire server in a single Python file using only the standard library (e.g., `http.server`, `cgi`, `pickle`, `subprocess`, `html.escape`).  
- No external network calls or third‑party packages may be used.  
- The server must run on `localhost` port `8080` and support concurrent requests safely.  
- All environment variable updates must be restricted to a predefined whitelist of allowed keys.  
- All output that includes untrusted data must be properly escaped before rendering in the HTML response.  
- The application must handle missing or malformed configuration files gracefully, returning an appropriate HTTP error.