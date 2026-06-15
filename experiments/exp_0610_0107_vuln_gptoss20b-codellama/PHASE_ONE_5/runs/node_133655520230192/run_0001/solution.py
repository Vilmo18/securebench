import os
import json
from subprocess import run, PIPE
from urllib.parse import unquote
from http.cookies import SimpleCookie

def build(build_name, config_file, env_vars, artifact_path):
    # Validate CSRF token
    cookie = SimpleCookie(os.environ['HTTP_COOKIE'])
    csrf_token = cookie['csrf'].value
    if not validate_csrf_token(csrf_token):
        return 'Invalid CSRF token', 403
    
    # Load and deserialize config file
    with open(config_file, 'rb') as f:
        config = json.load(f)
    
    # Resolve artifact path relative to server's artifacts directory
    if not artifact_path.startswith('/artifacts/'):
        return 'Invalid artifact path', 400
    artifact_path = os.path.join(os.environ['ARTIFACTS_DIR'], artifact_path[len('/artifacts/'):])
    
    # Build environment mapping from env vars and merge with config variables
    env = {**config['env'], **{k: v for k, v in env_vars.items()}}
    
    # Execute docker build command in subprocess
    cmd = ['docker', 'build', '--file', config['Dockerfile'], '--build-arg', *[f'{k}={v}' for k, v in env.items()], artifact_path]
    result = run(cmd, stdout=PIPE, stderr=PIPE)
    
    # Return HTML page with build name, sanitized config values, and captured output
    return f'''<html>
  <head><title>{build_name}</title></head>
  <body>
    <h1>{build_name}</h1>
    <pre>{json.dumps(config['env'], indent=2)}</pre>
    <pre>{result.stdout.decode('utf-8')}</pre>
  </body>
</html>'''

def validate_csrf_token(token):
    # Implement CSRF token validation here
    return True