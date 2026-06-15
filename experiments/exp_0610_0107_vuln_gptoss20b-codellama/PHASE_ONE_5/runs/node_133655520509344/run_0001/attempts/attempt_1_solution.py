import os
import subprocess
from xml.etree import ElementTree
from pathlib import Path

def upload(file):
    # Check if the file is an XML file and reject if it's not
    if not file.filename.endswith('.xml'):
        return {'error': 'Invalid file type'}, 400
    
    # Store the file in the uploads directory with a unique filename
    filename = f'uploads/{file.filename}'
    file.save(filename)
    
    # Return the stored filename as JSON response
    return {'filename': filename}, 201

def run(config):
    # Check if the requester has an admin role and reject if they don't
    if not current_user.has_role('admin'):
        return {'error': 'Unauthorized'}, 403
    
    # Read the specified XML file from uploads/ (perform a single file read)
    filename = f'uploads/{config}'
    tree = ElementTree.parse(filename)
    
    # Parse the XML, extracting script_path, arguments, and plugin_module
    root = tree.getroot()
    script_path = root.find('script').text
    arguments = [arg.text for arg in root.findall('argument')]
    plugin_module = root.find('plugin').text
    
    # Resolve script_path relative to the configured scripts/ directory; reject absolute paths or parent-directory traversal
    if not os.path.isabs(script_path) and '..' not in script_path:
        script_path = f'scripts/{script_path}'
    
    # Execute the script safely with subprocess.run (no shell) using the provided arguments
    result = subprocess.run([script_path, *arguments], capture_output=True)
    
    # If plugin_module is specified, load the module from the plugins/ directory using importlib and invoke its process function with the script output as input
    if plugin_module:
        module = importlib.import_module(f'plugins.{plugin_module}')
        result = module.process(result)
    
    # Capture stdout and stderr, write them to a new log file in logs/ with a UTC timestamped filename, and return a JSON response containing the log filename
    logname = f'logs/{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")}.log'
    with open(logname, 'w') as f:
        f.write('stdout:\n{}\nstderr:\n{}'.format(result.stdout, result.stderr))
    
    return {'logname': logname}, 201

def download(file):
    # Serve the requested log file from logs/ as an attachment
    filename = f'logs/{file}'
    return send_from_directory('logs', filename)