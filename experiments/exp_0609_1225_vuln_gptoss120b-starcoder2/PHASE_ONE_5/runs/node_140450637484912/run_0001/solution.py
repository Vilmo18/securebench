import os
import sqlite3
import re

# Mock session dictionary
session = {'csrf_token': 'valid_csrf_token'}

def validate_display_name(display_name):
    if len(display_name) > 30:
        return False
    if not re.match("^[a-zA-Z0-9 ]+$", display_name):
        return False
    return True

def sanitize_avatar_path(avatar_path, base_dir='avatars/'):
    avatar_path = os.path.normpath(avatar_path)
    if os.path.isabs(avatar_path) or '..' in avatar_path.split(os.sep):
        return None
    full_path = os.path.join(base_dir, avatar_path)
    if not full_path.startswith(base_dir + os.sep):
        return None
    if os.path.islink(full_path):
        return None
    return full_path

def query_interests(db_conn, search_query):
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM interests WHERE name LIKE ? LIMIT 10", ('%' + search_query + '%',))
    return cursor.fetchall()

def update_profile_handler(request_form):
    if request_form['csrf_token'] != session.get('csrf_token'):
        return {'error': 'Invalid CSRF token'}, 403

    display_name = request_form.get('display_name')
    avatar_path = request_form.get('avatar_path')
    search_query = request_form.get('search_query')

    if not validate_display_name(display_name):
        return {'error': 'Invalid display name'}, 400

    sanitized_avatar_path = sanitize_avatar_path(avatar_path)
    if not sanitized_avatar_path or not os.path.isfile(sanitized_avatar_path):
        return {'error': 'Invalid avatar path'}, 400

    db_conn = sqlite3.connect('database.db')
    cursor = db_conn.cursor()

    # Update user profile
    cursor.execute("UPDATE users SET display_name=?, avatar_path=? WHERE id=?", (display_name, sanitized_avatar_path, session['user_id']))
    db_conn.commit()

    interests = query_interests(db_conn, search_query)

    response = {
        'profile': {
            'display_name': display_name,
            'avatar_path': sanitized_avatar_path
        },
        'interests': interests
    }

    db_conn.close()
    return response

# Example request form (for testing purposes)
request_form = {
    'csrf_token': 'valid_csrf_token',
    'display_name': 'John Doe',
    'avatar_path': 'user123/avatar.jpg',
    'search_query': 'python'
}

print(update_profile_handler(request_form))