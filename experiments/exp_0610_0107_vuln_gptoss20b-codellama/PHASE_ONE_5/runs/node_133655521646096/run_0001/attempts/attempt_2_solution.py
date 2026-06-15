import os
import subprocess
import xml.etree.ElementTree as ET
from http import HTTPStatus
from typing import List, Optional

import psycopg2
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel

app = FastAPI()

SCRIPT_DIR: str = os.environ["SCRIPT_DIR"]
DB_HOST: str = os.environ["DB_HOST"]
DB_PORT: int = int(os.environ["DB_PORT"])
DB_USER: str = os.environ["DB_USER"]
DB_PASSWORD: str = os.environ["DB_PASSWORD"]
CONFIG_DIR: str = os.environ["CONFIG_DIR"]


class ScriptResult(BaseModel):
    stdout: Optional[str]
    stderr: Optional[str]
    exit_code: int


@app.get("/run-script")
async def run_script(name: str = Query(...)):
    script_path = os.path.join(SCRIPT_DIR, name)
    if not os.path.isfile(script_path):
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Script not found")
    if not os.access(script_path, os.X_OK):
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Script is not executable")
    result = await run_command(["python", script_path])
    return ScriptResult(stdout=result.stdout, stderr=result.stderr, exit_code=result.returncode)


@app.post("/db-query")
async def db_query(request: Request):
    sql = request.json()["sql"]
    params = request.json()["params"]
    if not isinstance(params, list):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Params must be a list")
    cursor = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return {"rows": rows}
    finally:
        cursor.close()


@app.post("/xml-data")
async def xml_data(request: Request):
    xml_data = request.json()["xml"]
    if not isinstance(xml_data, str):
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="XML data must be a string")
    tree = ET.fromstring(xml_data)
    for element in tree:
        print(element.tag, element.text)
    return {"message": "XML data parsed successfully"}