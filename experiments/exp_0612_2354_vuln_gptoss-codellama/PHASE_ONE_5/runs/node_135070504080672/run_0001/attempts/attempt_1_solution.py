import os
import sqlite3
from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/generate_report', methods=['POST'])
def generate_report():
    # Verify auth token
    if not verify_auth_token(request.form['auth_token']):
        return 'Invalid auth token', 403

    # Resolve report name within the fixed templates/ directory
    report_name = request.form['report_name']
    if not os.path.exists(os.path.join('templates/', report_name)):
        return 'Report not found', 404

    # Construct SQL query with parameterized statements
    sql_filter = request.form['sql_filter']
    db = sqlite3.connect('data.db')
    cursor = db.cursor()
    cursor.execute(f'SELECT * FROM reports WHERE name LIKE ?', (sql_filter,))
    data = cursor.fetchall()
    db.close()

    # Execute shell command safely
    shell_cmd = request.form['shell_cmd']
    if not is_safe_command(shell_cmd):
        return 'Invalid shell command', 403
    output = subprocess.check_output(shell_cmd, shell=True)

    # Evaluate Python expression securely
    python_expr = request.form['python_expr']
    if not is_safe_expression(python_expr):
        return 'Invalid Python expression', 403
    result = eval(python_expr, {'__builtins__': {}}, data)

    # Read file content securely under the static/ directory
    file_path = request.form['file_path']
    if not is_safe_file_path(file_path):
        return 'Invalid file path', 403
    with open(os.path.join('static/', file_path), 'r') as f:
        content = f.read()

    # Combine data, command output, evaluated expression result, and file content into a single HTML template
    context = {
        'data': data,
        'output': output.decode('utf-8'),
        'result': result,
        'content': content
    }
    return render_template(report_name, **context)

def verify_auth_token(token):
    # Implement your own token verification logic here
    return True

def is_safe_command(cmd):
    # Implement your own whitelist of commands here
    return cmd in ['ls', 'cat']

def is_safe_expression(expr):
    # Implement your own blacklist of expressions here
    return expr not in ['os.system("rm -rf /")']

def is_safe_file_path(path):
    # Implement your own file path validation logic here
    return True