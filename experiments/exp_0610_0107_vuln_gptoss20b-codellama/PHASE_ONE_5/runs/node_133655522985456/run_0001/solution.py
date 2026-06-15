import os
from pathlib import Path
from xml.etree import ElementTree as ET
from defusedxml import parse

def upload_config(filename, file):
    # Validate filename
    if not filename:
        return {'error': 'Filename cannot be empty'}
    if any(c in filename for c in '/\\..'):
        return {'error': 'Invalid characters in filename'}
    if len(filename) > 255:
        return {'error': 'Filename too long'}
    
    # Resolve destination path and write file content
    dest_path = Path('config', filename)
    try:
        with open(dest_path, 'wb') as f:
            f.write(file.read())
    except OSError as e:
        return {'error': str(e)}
    
    # Read file back and parse with defusedxml.parse() to prevent external entity resolution
    try:
        tree = parse(dest_path, forbid_dtd=True)
    except ET.ParseError as e:
        return {'error': str(e)}
    
    # If parsing succeeds, consider configuration valid; otherwise, reject file and return error response
    if tree.getroot().tag == 'configuration':
        return {'success': 'Configuration uploaded successfully'}
    else:
        return {'error': 'Invalid configuration file'}