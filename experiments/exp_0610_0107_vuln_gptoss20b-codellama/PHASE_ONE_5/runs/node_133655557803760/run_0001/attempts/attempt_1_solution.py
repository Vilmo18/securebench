import os
import sys

PLUGINS_DIR = "/opt/mytool/plugins"

def load_plugin(path):
    # Resolve the path to an absolute path
    abs_path = os.path.abspath(path)
    
    # Verify that the absolute path is located under PLUGINS_DIR
    if not abs_path.startswith(PLUGINS_DIR):
        raise ValueError("Plugin path must be within the /opt/mytool/plugins directory")
    
    # Open the plugin file and import it as a module
    try:
        with open(abs_path, "rb") as f:
            plugin = imp.load_module("plugin", f, abs_path, (".py", "r", imp.PY_SOURCE))
    except FileNotFoundError:
        raise ValueError("Plugin file not found")
    
    # Call the run() function of the plugin module
    try:
        output = plugin.run()
    except AttributeError:
        raise ValueError("Plugin does not have a run() function")
    
    return output

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: mytool <plugin_path>")
        sys.exit(1)
    
    path = sys.argv[1]
    try:
        output = load_plugin(path)
        print(output)
    except ValueError as e:
        print(f"Error loading plugin: {e}")