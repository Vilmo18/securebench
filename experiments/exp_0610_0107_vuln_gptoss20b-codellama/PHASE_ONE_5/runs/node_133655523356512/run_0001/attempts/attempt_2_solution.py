import os
from http import HTTPStatus
from pathlib import Path
from typing import Optional

import jwt
from fastapi import FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import StreamingResponse

app = FastAPI()

SECURE_FILES_DIR = "secure_files/"
ALLOWED_EXTENSIONS = ["txt", "pdf"]


@app.get("/api/files/download")
async def download_file(
    file: str,
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer()),
):
    if not authorization or not authorization.credentials:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)

    try:
        payload = jwt.decode(authorization.credentials, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)

    if not payload.get("role") == "admin":
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)

    file = Path(file).resolve()
    if not file.is_relative_to(SECURE_FILES_DIR):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    if not file.exists():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    if not file.suffix in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN)

    return StreamingResponse(file.open("rb"), media_type="application/octet-stream")