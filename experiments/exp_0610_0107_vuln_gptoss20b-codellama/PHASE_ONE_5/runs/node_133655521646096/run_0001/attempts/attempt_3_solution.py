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


@app.get("/run-sql")
async def run_sql(query: str):
    conn = psycopg2.connect(dbname="mydatabase", user="myuser", password="mypassword", host="localhost", port="5432")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return {"results": results}
    finally:
        cursor.close()
        conn.close()


@app.post("/parse-xml")
async def parse_xml(xml_data: str):
    try:
        tree = ET.fromstring(xml_data)
        for element in tree:
            print(element.tag, element.text)
    except Exception as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Invalid XML data") from e