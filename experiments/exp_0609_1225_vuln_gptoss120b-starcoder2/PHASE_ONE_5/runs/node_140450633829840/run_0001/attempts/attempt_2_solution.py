import os
import defusedxml.ElementTree as ET
import sqlite3

UPLOAD_DIR = 'imports/'
os.makedirs(UPLOAD_DIR, exist_ok=True)

def sanitize_filename(filename):
    # Reject absolute paths, parent-directory traversal (`..`), and null bytes.
    if os.path.isabs(filename) or '..' in filename or '\0' in filename:
        return None
    return os.path.basename(filename)

def handle_upload(file_field):
    filename = sanitize_filename(file_field.filename)
    if not filename:
        return {'status': 'error', 'message': 'Invalid file name.'}

    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(file_field.file.read())

    return {'status': 'success', 'filepath': filepath}

def process_import(filepath):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError:
        return {'status': 'error', 'message': 'Invalid XML file.'}

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    user_count = 0
    for user in root.findall('user'):
        username = user.find('username')
        email = user.find('email')

        if not username or not email:
            print(f'Warning: Missing required fields for user {ET.tostring(user)}')
            continue

        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)",
                       (username.text, email.text))
        user_count += 1

    conn.commit()
    conn.close()

    return {'status': 'success', 'user_count': user_count}

def import_handler(file_field):
    upload_result = handle_upload(file_field)
    if upload_result['status'] == 'error':
        return upload_result

    process_result = process_import(upload_result['filepath'])
    return process_result