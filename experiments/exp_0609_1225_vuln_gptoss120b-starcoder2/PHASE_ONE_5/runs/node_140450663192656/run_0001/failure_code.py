import defusedxml.ElementTree as ET
import sqlite3
import os
import re
import subprocess

def import_config_and_generate_report(xml_bytes):
    # Parse XML securely, disabling external entity resolution
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError("Invalid XML format") from e

    # Validate root element and required child elements
    if root.tag != 'config':
        raise ValueError("Root element must be <config>")
    db_query = root.find('db_query').text
    script_path = root.find('script_path').text
    report_name = root.find('report_name').text

    # Validate that all required elements contain only printable ASCII characters
    if not (all(c.isprintable() for c in db_query) and
            all(c.isprintable() for c in script_path) and
            all(c.isprintable() for c in report_name)):
        raise ValueError("All elements must contain only printable ASCII characters")

    # Execute the SQL statement from <db_query> against a local SQLite database
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    try:
        cursor.execute(db_query)
        temp_table_name = 'temp_table'
        cursor.execute(f"CREATE TEMP TABLE {temp_table_name} AS SELECT * FROM ({db_query})")
    except sqlite3.Error as e:
        raise ValueError("SQL query execution failed") from e
    finally:
        conn.close()

    # Construct the shell command and ensure it is safe
    reports_dir = 'reports/'
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    report_path = os.path.join(reports_dir, f"{report_name}.csv")
    if not re.match(r'^reports/[\w\-\.]+$', report_path) or '..' in report_path:
        raise ValueError("Invalid report path")

    # Execute the shell command to produce a CSV report file
    try:
        subprocess.run([script_path, temp_table_name], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ValueError("Script execution failed") from e

    return True