import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote
from subprocess import run, PIPE
from secrets import token_hex

class FileManager:
    def __init__(self):
        self.base_dir = '/var/app/data'
        self.csrf_token = token_hex(16)
    
    def _get_user_dir(self, user_id):
        return os.path.join(self.base_dir, str(user_id))
    
    def upload(self, file, target_folder):
        if not Path(file).is_file():
            raise ValueError('File does not exist')
        
        user_id = self._get_user_id()
        user_dir = self._get_user_dir(user_id)
        target_path = os.path.join(user_dir, target_folder)
        
        if not Path(target_path).is_dir():
            raise ValueError('Target folder does not exist')
        
        file_name = Path(file).name
        target_file = os.path.join(target_path, file_name)
        
        if os.path.exists(target_file):
            raise ValueError('File already exists')
        
        with open(file, 'rb') as f:
            data = f.read()
        
        with open(target_file, 'wb') as f:
            f.write(data)
    
    def download(self, file):
        user_id = self._get_user_id()
        user_dir = self._get_user_dir(user_id)
        
        file_path = os.path.join(user_dir, file)
        if not Path(file_path).is_file():
            raise ValueError('File does not exist')
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return data
    
    def delete(self, file):
        user_id = self._get_user_id()
        user_dir = self._get_user_dir(user_id)
        
        file_path = os.path.join(user_dir, file)
        if not Path(file_path).is_file():
            raise ValueError('File does not exist')
        
        os.remove(file_path)
    
    def execute(self, script):
        user_id = self._get_user_id()
        user_dir = self._get_user_dir(user_id)
        
        script_path = os.path.join(user_dir, script)
        if not Path(script_path).is_file():
            raise ValueError('Script does not exist')
        
        result = run(['python', script_path], stdout=PIPE, stderr=PIPE)
        return result.stdout.decode()
    
    def _get_user_id(self):
        user_id = os.environ['USER']
        if not user_id:
            raise ValueError('User ID is not set')
        
        return user_id