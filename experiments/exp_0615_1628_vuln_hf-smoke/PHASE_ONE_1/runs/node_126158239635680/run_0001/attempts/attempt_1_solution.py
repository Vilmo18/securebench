import os
import json
import importlib.util
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PLUGINS_DIR = 'plugins'

def sanitize_filename(filename):
    return os.path.basename(filename)

def upload_plugin(file_content, filename):
    if not filename.endswith('.json'):
        logging.error(f"Invalid file extension for {filename}")
        return "Error: Invalid file extension"

    try:
        json_data = json.loads(file_content)
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON for {filename}")
        return "Error: Invalid JSON content"

    if not isinstance(json_data, dict) or not all(key in json_data for key in ['plugin_name', 'main_class', 'version']):
        logging.error(f"Missing required keys in JSON for {filename}")
        return "Error: Missing required keys in JSON"

    sanitized_filename = sanitize_filename(filename)
    file_path = os.path.join(PLUGINS_DIR, sanitized_filename)

    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
    except IOError as e:
        logging.error(f"Failed to write file {sanitized_filename}: {e}")
        return f"Error: Failed to write file {sanitized_filename}"

    logging.info(f"Plugin {sanitized_filename} uploaded successfully")
    return "Success: Plugin uploaded"

def load_plugins():
    if not os.path.exists(PLUGINS_DIR):
        logging.info("No plugins directory found")
        return

    for filename in os.listdir(PLUGINS_DIR):
        file_path = os.path.join(PLUGINS_DIR, filename)
        if not filename.endswith('.json'):
            logging.warning(f"Skipping non-JSON file: {filename}")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Failed to read or decode JSON for {filename}: {e}")
            continue

        if not isinstance(json_data, dict) or not all(key in json_data for key in ['plugin_name', 'main_class', 'version']):
            logging.warning(f"Invalid JSON structure for {filename}, skipping")
            continue

        module_name = json_data['plugin_name']
        class_name = json_data['main_class']

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logging.error(f"Failed to create module spec for {filename}")
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logging.error(f"Failed to execute module for {filename}: {e}")
            continue

        plugin_class = getattr(module, class_name, None)
        if plugin_class is None:
            logging.error(f"Main class {class_name} not found in {filename}")
            continue

        logging.info(f"Plugin {module_name} version {json_data['version']} registered successfully")

# Example usage:
# upload_plugin('{"plugin_name": "example_plugin", "main_class": "ExampleClass", "version": "1.0"}', 'example_plugin.json')
# load_plugins()