import os
import zipfile
import defusedxml.ElementTree as ET
import sqlite3
import subprocess
from urllib.parse import unquote

def sanitize_filename(filename):
    return ''.join(c if c.isalnum() else '_' for c in filename).strip('_')[:50]

def validate_zip_entry(entry, base_dir):
    entry_path = os.path.join(base_dir, entry.filename)
    if not entry_path.startswith(os.path.abspath(base_dir)) or '..' in entry.filename:
        return False
    return True

def handle_request(archive_file):
    import_dir = 'imports/'
    os.makedirs(import_dir, exist_ok=True)

    filename = sanitize_filename(unquote(archive_file.filename))
    extract_path = os.path.join(import_dir, filename)
    os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(archive_file.file) as z:
        for entry in z.infolist():
            if not validate_zip_entry(entry, extract_path):
                return {'error': 'Invalid path in archive'}, 400
            z.extract(entry, extract_path)

    manifest_path = os.path.join(extract_path, 'profile.xml')
    tree = ET.parse(manifest_path)
    root = tree.getroot()

    conn = sqlite3.connect('employee.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS employee_data (field TEXT, value TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS employee_meta (field TEXT, value TEXT)')

    for emp in root.findall('employee'):
        csv_file = os.path.join(extract_path, emp.find('csv').text)
        if not os.path.isfile(csv_file):
            return {'error': f'CSV file {csv_file} not found'}, 400

        with open(csv_file) as f:
            for line in f:
                field, value = line.strip().split(',', 1)
                cursor.execute('INSERT INTO employee_data (field, value) VALUES (?, ?)', (field, value))

        meta = emp.find('meta')
        if meta is not None:
            for m in meta.findall('*'):
                cursor.execute('INSERT INTO employee_meta (field, value) VALUES (?, ?)', (m.tag, m.text))

    conn.commit()
    subprocess.run(['/usr/bin/env', 'python3', os.path.join(os.path.dirname(__file__), 'generate_emails.py'), extract_path], check=True)

    return {'status': 'success'}, 200