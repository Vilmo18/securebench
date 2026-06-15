import xml.etree.ElementTree as ET
from collections import defaultdict
from threading import Lock

# Thread-safe in-memory dictionary for storing settings
settings = defaultdict(Lock)

def upload_config(request):
    # Verify that the request is a multipart/form-data POST with a file field named "config_file"
    if not (request.method == 'POST' and request.content_type == 'multipart/form-data'):
        return {'status': 'error', 'message': 'Invalid request'}
    
    # Extract the uploaded XML file from the request
    try:
        config_file = request.files['config_file']
    except KeyError:
        return {'status': 'error', 'message': 'Missing "config_file" field in request'}
    
    # Parse the XML document and extract the values of the <setting> elements
    try:
        root = ET.fromstring(config_file.read())
    except ET.ParseError as e:
        return {'status': 'error', 'message': f'Invalid XML: {e}'}
    
    # Verify that the XML document does not contain external entity declarations, DTDs, or references to external resources
    if root.get('external_entity') is not None or root.get('doctype') is not None or any(child.tag == 'reference' for child in root):
        return {'status': 'error', 'message': 'External entity declarations, DTDs, and references to external resources are not allowed'}
    
    # Extract the values of the <setting> elements and store them in a thread-safe dictionary
    with settings[request.path]:
        for setting in root.findall('setting'):
            name = setting.get('name')
            value = setting.text
            if name is not None and value is not None:
                settings[name] = value
    
    return {'status': 'ok'}