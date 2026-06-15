import os
import base64
import pickle
from pathlib import Path
from http import HTTPStatus

UPLOADS_DIR = "uploads"
ALLOWED_FILENAME_CHARS = set(Path().as_posix()) - {"/", ".", ".."}

def upload(request):
    try:
        data = request.json()
        filename = data["filename"]
        file_data = base64.b64decode(data["file_data"])
        metadata = pickle.loads(base64.b64decode(data["metadata"]))
    except (KeyError, TypeError):
        return HTTPStatus.BAD_REQUEST
    
    if not filename or any(c not in ALLOWED_FILENAME_CHARS for c in filename):
        return HTTPStatus.FORBIDDEN
    
    target_path = os.path.join(UPLOADS_DIR, filename)
    with open(target_path, "wb") as f:
        f.write(file_data)
    
    try:
        metadata = {k: v for k, v in metadata.items() if isinstance(k, str) and isinstance(v, str)}
        # apply any valid metadata attributes to the stored file (e.g., set file tags or permissions)
    except pickle.UnpicklingError:
        return HTTPStatus.BAD_REQUEST
    
    return HTTPStatus.CREATED