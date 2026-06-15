import os
import json
from importlib import import_module
from pathlib import Path
from urllib.parse import unquote

def upload_plugin(request):
    plugin_name = request.form['plugin_name']
    plugin_code = request.form['plugin_code']
    
    if not plugin_name.endswith('.py') or '/' in plugin_name or '\\' in plugin_name:
        return json.dumps({'error': 'Invalid plugin name.'}), 400
    
    plugins_dir = Path('plugins/')
    target_path = plugins_dir / unquote(plugin_name)
    if not target_path.resolve().parent == plugins_dir:
        return json.dumps({'error': 'Invalid plugin name.'}), 400
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(plugin_code)
    
    try:
        import_module(plugin_name[:-3])
    except Exception as e:
        return json.dumps({'error': str(e)}), 500
    
    return json.dumps({'success': True}), 201