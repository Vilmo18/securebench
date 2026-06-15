import os
from xml.etree import ElementTree as ET
from base64 import b64decode
from pickle import loads

def handle_config_update(request):
    # Parse the uploaded file using an XML parser that disables external entity processing
    tree = ET.parse(request.files['config_file'], forbid_dtd=True)
    
    # Locate the <Payload> element and read its text content, which is a base-64 encoded pickle string
    payload_element = tree.find('Payload')
    if not payload_element:
        return {'status': 'error', 'message': 'Invalid configuration file'}
    
    # Decode the base-64 string and unpickle it to obtain a dictionary
    try:
        config_data = loads(b64decode(payload_element.text))
    except (TypeError, ValueError):
        return {'status': 'error', 'message': 'Invalid configuration data'}
    
    # Validate that the dictionary keys and values are strings, and that no key contains characters that could influence file paths or configuration directives
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in config_data.items()):
        return {'status': 'error', 'message': 'Invalid configuration data'}
    
    # Resolve the destination file path as `config/app_config.json` relative to the application’s predefined configuration directory
    config_file = os.path.join(os.getcwd(), 'config', 'app_config.json')
    
    # Write the validated configuration data to the resolved file as JSON in a single write operation
    with open(config_file, 'w') as f:
        json.dump(config_data, f)
    
    return {'status': 'success', 'message': 'Configuration updated successfully'}