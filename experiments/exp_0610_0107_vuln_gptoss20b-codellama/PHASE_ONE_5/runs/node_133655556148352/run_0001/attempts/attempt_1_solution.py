import json
from html import escape
from http import HTTPStatus

def handle_profile_page(request):
    config = request.form['config']
    try:
        data = json.loads(config)
    except json.JSONDecodeError as e:
        return 'Invalid JSON', HTTPStatus.BAD_REQUEST
    
    if not isinstance(data, list):
        return 'Top-level object must be an array', HTTPStatus.BAD_REQUEST
    
    for field in data:
        if not isinstance(field, dict) or 'type' not in field or 'label' not in field:
            return 'Invalid field descriptor', HTTPStatus.BAD_REQUEST
        
        type = field['type']
        label = field['label']
        if type not in ('text', 'date', 'email'):
            return f'Invalid field type "{type}"', HTTPStatus.BAD_REQUEST
        
        placeholder = ''
        if type == 'text':
            placeholder = 'Enter text...'
        elif type == 'date':
            placeholder = 'YYYY-MM-DD'
        elif type == 'email':
            placeholder = 'example@domain.com'
        
        escaped_label = escape(label)
        html = f'<div><label>{escaped_label}</label><input type="{type}" placeholder="{placeholder}"></div>'
    
    return html, HTTPStatus.OK