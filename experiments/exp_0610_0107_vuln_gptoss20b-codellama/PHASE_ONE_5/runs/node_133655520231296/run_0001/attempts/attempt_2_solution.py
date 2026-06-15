import os
from http import HTTPStatus
from pathlib import Path
from shutil import make_archive
from subprocess import run, PIPE

CONFIG_DIR = "configs"
ALLOWED_EXTENSIONS = ["txt", "conf"]

def upload(file):
    filename = file.filename
    if not filename:
        return HTTPStatus.BAD_REQUEST
    
    target_path = os.path.join(CONFIG_DIR, filename)
    if not target_path.startswith(CONFIG_DIR + os.sep):
        return HTTPStatus.FORBIDDEN
    
    file.save(target_path)
    return HTTPStatus.OK

def view(filename):
    if not filename:
        return HTTPStatus.NOT_FOUND
    
    target_path = os.path.join(CONFIG_DIR, filename)
    if not Path(target_path).exists():
        return HTTPStatus.NOT_FOUND
    
    with open(target_path, "r") as f:
        return f.read()

def download(filename):
    if not filename:
        return HTTPStatus.NOT_FOUND
    
    target_path = os.path.join(CONFIG_DIR, filename)
    if not Path(target_path).exists():
        return HTTPStatus.NOT_FOUND
    
    with open(target_path, "rb") as f:
        response = make_response()
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.data = f.read()
        return response

def backup(filename):
    if not filename:
        return HTTPStatus.NOT_FOUND
    
    target_path = os.path.join(CONFIG_DIR, filename)
    if not Path(target_path).exists():
        return HTTPStatus.NOT_FOUND
    
    command = f"tar -czf backup_{filename}.tar.gz {target_path}"
    result = run(command, shell=False, stdout=PIPE, stderr=PIPE)
    if result.returncode != 0:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    
    return HTTPStatus.OK

def delete(filename):
    if not filename:
        return HTTPStatus.NOT_FOUND
    
    target_path = os.path.join(CONFIG_DIR, filename)
    if not Path(target_path).exists():
        return HTTPStatus.NOT_FOUND
    
    os.remove(target_path)
    return HTTPStatus.OK