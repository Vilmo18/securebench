import json
from http import HTTPStatus
from secrets import token_hex
from typing import Optional

from fastapi import FastAPI, Cookie, Depends, Header, Request, Response
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

app = FastAPI()

# Define the API key rotation endpoint
@app.post("/rotate_api_key")
async def rotate_api_key(request: Request, response: Response):
    # Extract the session cookie and determine the authenticated user's ID and role
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return JSONResponse({"detail": "Missing session cookie"}, status_code=HTTPStatus.UNAUTHORIZED)
    user_id, role = await get_user_info(session_cookie)
    if not user_id or not role:
        return JSONResponse({"detail": "Invalid session cookie"}, status_code=HTTPStatus.UNAUTHORIZED)
    
    # Verify that the authenticated user has either the developer or admin role; otherwise, respond with HTTP 403 Forbidden
    if role not in ("developer", "admin"):
        return JSONResponse({"detail": f"User {user_id} does not have sufficient permissions"}, status_code=HTTPStatus.FORBIDDEN)
    
    # Validate the key name: length between 3 and 50 characters, contains only alphanumeric characters, dashes, or underscores, must not contain null bytes or non-printable characters
    try:
        key_name = request.json()["key_name"]
    except (KeyError, ValidationError):
        return JSONResponse({"detail": "Invalid key name"}, status_code=HTTPStatus.BAD_REQUEST)
    
    if not 3 <= len(key_name) <= 50:
        return JSONResponse({"detail": f"Key name must be between 3 and 50 characters"}, status_code=HTTPStatus.BAD_REQUEST)
    
    if not re.match("^[a-zA-Z0-9_-]+$", key_name):
        return JSONResponse({"detail": f"Key name must contain only alphanumeric characters, dashes, or underscores"}, status_code=HTTPStatus.BAD_REQUEST)
    
    # Generate a cryptographically secure random API key string
    api_key = token_hex(32)
    
    # Store the new key and its metadata (user ID, key name, creation timestamp) in the database with a single write operation
    await store_api_key(user_id, key_name, api_key)
    
    # Return HTTP 200 OK with a JSON body that includes the new key’s identifier and the key value
    return JSONResponse({"id": f"{user_id}-{key_name}", "value": api_key})