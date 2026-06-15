import json
from datetime import datetime
from xml.etree.ElementTree import ElementTree, XMLParser
from jwt import decode as jwt_decode

def upload_config(request):
    # Validate JWT and ensure user has admin role
    jwt = request.headers['Authorization']
    payload = jwt_decode(jwt, verify=True)
    if not payload['role'] == 'admin':
        return json.dumps({'success': False, 'message': 'Unauthorized'}), 403
    
    # Read XML payload from request body
    xml = ElementTree(XMLParser(resolve_entities=False)).fromstring(request.data)
    
    # Locate optional <script> element and extract its text content
    script = xml.find('.//script')
    if script is not None:
        script_text = script.text
        
        # Execute extracted script in a restricted evaluation context
        result = eval(script_text, {'__builtins__': {}})
    
    # Return JSON response indicating success or failure, and any output produced by the script
    return json.dumps({'success': True, 'output': result}), 200