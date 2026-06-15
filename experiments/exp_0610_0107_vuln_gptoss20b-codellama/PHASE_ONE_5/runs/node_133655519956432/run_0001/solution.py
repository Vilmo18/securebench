import os
from http import HTTPStatus
from pathlib import Path
from typing import Optional

def view(file: str, preview: bool = False) -> str:
    if not file.startswith("docs/"):
        return f"Invalid file path: {file}", HTTPStatus.BAD_REQUEST
    
    resolved_path = os.path.join(os.getcwd(), file)
    if preview:
        output = os.popen(f"cat {resolved_path}").read()
    else:
        with open(resolved_path, "r") as f:
            output = f.read()
    
    return f'<html><body>{output}</body></html>', HTTPStatus.OK

def upload_xml(data: str) -> str:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        return f"Invalid XML payload: {e}", HTTPStatus.BAD_REQUEST
    
    text = root.text or ""
    return f'<html><body>{text}</body></html>', HTTPStatus.OK