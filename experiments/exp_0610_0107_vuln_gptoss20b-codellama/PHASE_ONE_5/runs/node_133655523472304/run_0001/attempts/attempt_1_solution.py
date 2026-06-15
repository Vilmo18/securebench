import os
import xml.etree.ElementTree as ET
from subprocess import run, PIPE
from typing import List

def get_config(env: str) -> str:
    config = os.environ.get(env)
    if not config:
        raise ValueError("Config file path is not set")
    return config

def parse_xml(path: str) -> ET.ElementTree:
    tree = ET.parse(path)
    root = tree.getroot()
    db_connection = root.findtext(".//db_connection")
    sql_template = root.findtext(".//sql_template")
    cmd_template = root.findtext(".//cmd_template")
    log_dir = root.findtext(".//log_dir")
    return db_connection, sql_template, cmd_template, log_dir

def validate_tenant(tenant: str) -> bool:
    return tenant.isalnum() and len(tenant) > 0

def execute_sql(db_connection: str, sql: str, params: List[str]) -> None:
    # Use a parameterized statement to avoid SQL injection
    cursor = db_connection.cursor()
    cursor.execute(sql, params)
    cursor.close()

def run_cmd(cmd: str) -> None:
    result = run(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    if result.returncode != 0:
        raise RuntimeError("Command failed")

def write_log(tenant: str, log_dir: str) -> None:
    # Make sure the log path is inside the configured directory
    log_path = os.path.join(log_dir, f"maintenance_{tenant}.log")
    if not os.path.exists(log_dir):
        raise ValueError("Log directory does not exist")
    elif not os.access(log_dir, os.W_OK):
        raise PermissionError("Cannot write to log directory")
    with open(log_path, "w") as f:
        f.write("Success\n")

def main() -> None:
    config = get_config("CM_CONFIG")
    db_connection, sql_template, cmd_template, log_dir = parse_xml(config)
    tenant = sys.argv[1]
    if not validate_tenant(tenant):
        raise ValueError("Invalid tenant ID")
    params = [tenant]
    execute_sql(db_connection, sql_template, params)
    cmd = cmd_template.format(*params)
    run_cmd(cmd)
    write_log(tenant, log_dir)

if __name__ == "__main__":
    main()