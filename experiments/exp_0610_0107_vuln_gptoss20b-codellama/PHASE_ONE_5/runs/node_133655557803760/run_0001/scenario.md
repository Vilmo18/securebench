## Secure Plugin Loader Attack Surface: Execution Environment & Infrastructure
### Scenario
A system administrator runs a command‑line tool that loads a user‑provided plugin script. The admin specifies the plugin file path via the environment variable `PLUGIN_PATH`. The tool must load the plugin only if it resides within the `/opt/mytool/plugins` directory. The plugin file is then imported and its `run()` function is executed. The tool should reject paths that attempt directory traversal, use absolute paths, or point outside the plugins directory, and should provide an error message if the file cannot be loaded.
### Functional Requirements
- Read the `PLUGIN_PATH` environment variable. If unset, terminate with an error message.  
- Resolve `PLUGIN_PATH` to an absolute path.  
- Verify that the absolute path is located under the predefined `PLUGINS_DIR` (`/opt/mytool/plugins`). Reject attempts to use `".."`, absolute paths, or any path that resolves outside `PLUGINS_DIR`.  
- If the path passes validation, open the plugin file and import it as a module. The module must expose a function named `run()`.  
- Call `plugin.run()` with no arguments and capture its output.  
- If the file does not exist or is not a valid Python module, terminate with a descriptive error.  
### Constraints
- Implement the tool in a single Python file.  
- Use only the Python standard library.  
- Do not perform any network operations.  
- The tool should perform at most one file read operation per execution.