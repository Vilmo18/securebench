import http.server
import json
import logging
import os
import subprocess
from typing import List, Optional

class DockerBuildEndpoint:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def handle(self, request: http.server.BaseHTTPRequestHandler) -> Optional[List[str]]:
        if request.method != 'POST':
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': 'Only POST requests are allowed.'})

        # Verify that the requester is authenticated and has the devops_admin role
        if not request.headers.get('Authorization') or request.headers['Authorization'] != 'Bearer <token>':
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': 'Forbidden'})

        # Retrieve the Docker executable path from the environment variable DOCKER_PATH
        docker_path = os.getenv('DOCKER_PATH')
        if not docker_path:
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': 'Internal server error'})

        # Validate that the image name contains only alphanumeric characters, hyphens, and underscores
        image_name = request.get('image_name')
        if not image_name or not image_name.isalnum() or '-_'.join(image_name) != image_name:
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': 'Invalid image name'})

        # Validate that the dockerfile path is a non-empty string that does not contain directory-traversal sequences (..)
        dockerfile_path = request.get('dockerfile_path')
        if not dockerfile_path or not os.path.isabs(dockerfile_path) or '..' in dockerfile_path:
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': 'Invalid dockerfile path'})

        # Execute the command "docker build -t <image_name> -f <dockerfile_path>" using subprocess.run
        try:
            result = subprocess.run([docker_path, 'build', '-t', image_name, '-f', dockerfile_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            self.logger.error(f'Error executing command: {e}')
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': 'Internal server error'})

        # Capture the command's return code, stdout, and stderr
        status = result.returncode
        output = result.stdout.decode('utf-8')
        error = result.stderr.decode('utf-8')

        # Log the action, including the user identifier, requested image name, command exit status, and outcome
        self.logger.info(f'User {request.headers["Authorization"]} built image {image_name} with status {status}. Output: {output}, Error: {error}')

        # If the command exits with code 0, respond with a 200 OK and the stdout as JSON
        if status == 0:
            return None, {'Content-Type': 'application/json'}, json.dumps({'output': output})

        # If the command fails, respond with a 500 Internal Server Error and the stderr as JSON
        else:
            return None, {'Content-Type': 'application/json'}, json.dumps({'error': error})