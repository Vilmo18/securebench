import os
from pathlib import Path
from xml.etree import ElementTree as ET
from pickle import loads, HIGHEST_PROTOCOL
from http.cookies import SimpleCookie
from cgi import FieldStorage
from tempfile import NamedTemporaryFile
from subprocess import run

def parse_xml(data):
    parser = ET.XMLParser(resolve_entities=False)
    tree = ET.parse(data, parser)
    return tree.getroot()

def validate_filename(filename):
    if filename is None or len(filename) == 0:
        raise ValueError("Invalid filename")
    if os.path.isabs(filename) or ".." in filename:
        raise ValueError("Absolute paths and parent references are not allowed")
    if "\x00" in filename:
        raise ValueError("Null bytes are not allowed in filenames")
    return filename

def validate_csrf_token(request):
    cookie = SimpleCookie()
    cookie.load(request.headers["Cookie"])
    csrf_token = cookie["csrf"].value
    if csrf_token != request.form["csrf"]:
        raise ValueError("Invalid CSRF token")

def execute_script(script):
    with NamedTemporaryFile() as f:
        f.write(script)
        run([sys.executable, f.name], check=True)

def handle_upload(request):
    if request.method != "POST":
        raise ValueError("Invalid method")
    form = FieldStorage(fp=request.body, environ=request.environ)
    config_file = form["config"]
    state_file = form["state"]
    validate_filename(config_file.filename)
    validate_filename(state_file.filename)
    xml = parse_xml(config_file.value)
    state = loads(state_file.value, HIGHEST_PROTOCOL)
    validate_csrf_token(request)
    execute_script(form["script"].value)
    return "Success"