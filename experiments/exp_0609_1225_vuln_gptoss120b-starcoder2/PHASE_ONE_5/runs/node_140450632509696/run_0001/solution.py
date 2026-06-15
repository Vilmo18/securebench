import os
import pathlib
from defusedxml.ElementTree import parse as safe_parse
import subprocess
import sqlite3

UPLOADS_DIR = 'uploads/'
JOB_OUTPUTS_DIR = 'job_outputs/'
ALLOWED_COMMANDS = {'ls', 'cat', 'grep'}
ALLOWED_TABLES = {'jobs', 'results'}

def validate_command(command):
    parts = command.split()
    if not parts or parts[0] not in ALLOWED_COMMANDS:
        return False
    for part in parts[1:]:
        if part.startswith('-') and part != '-E':
            return False
    return True

def validate_sql(sql):
    sql_lower = sql.lower().strip()
    if ';' in sql or '--' in sql or '/*' in sql:
        return False
    keywords = {'insert', 'update', 'delete', 'drop'}
    for keyword in keywords:
        if keyword in sql_lower.split():
            return False
    allowed_tables = set()
    for table in ALLOWED_TABLES:
        allowed_tables.update({table, f'"{table}"', f"'{table}'"})
    words = sql_lower.split()
    for word in words:
        if word.startswith('from') or word.startswith('join'):
            continue
        if word not in allowed_tables and not word.isalnum():
            return False
    return True

def validate_output_dir(output_dir):
    output_path = pathlib.Path(JOB_OUTPUTS_DIR) / output_dir
    try:
        relative_path = output_path.relative_to(JOB_OUTPUTS_DIR)
    except ValueError:
        return False
    if not output_path.is_relative_to(JOB_OUTPUTS_DIR):
        return False
    return True

def process_job(job_id):
    job_filepath = pathlib.Path(UPLOADS_DIR) / f"{job_id}.xml"
    try:
        tree = safe_parse(str(job_filepath))
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError):
        return "Invalid XML file", 400

    command = root.find('command').text
    sql = root.find('sql').text
    output_dir = root.find('outputDir').text

    if not validate_command(command):
        return "Invalid command", 400
    if not validate_sql(sql):
        return "Invalid SQL statement", 400
    if not validate_output_dir(output_dir):
        return "Invalid output directory", 400

    try:
        result = subprocess.run(command, shell=False, capture_output=True, text=True)
    except FileNotFoundError:
        return "Command not found", 500
    except Exception as e:
        return f"Failed to execute command: {e}", 500

    output_path = pathlib.Path(JOB_OUTPUTS_DIR) / output_dir / 'result.txt'
    try:
        os.makedirs(output_path.parent, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(result.stdout)
    except Exception as e:
        return f"Failed to write result: {e}", 500

    conn = sqlite3.connect('internal.db')
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
    except sqlite3.Error as e:
        return f"SQL execution failed: {e}", 500
    finally:
        conn.close()

    return "Job completed successfully", 200