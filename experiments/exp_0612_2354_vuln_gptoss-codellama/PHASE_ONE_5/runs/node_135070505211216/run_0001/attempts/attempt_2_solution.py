import os
import sqlite3
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set the directory for uploaded scripts
UPLOAD_FOLDER = 'config_scripts'
ALLOWED_EXTENSIONS = {'py', 'sql'}

# Connect to the SQLite database
conn = sqlite3.connect('configurations.db')
cur = conn.cursor()

@app.route('/upload', methods=['POST'])
def upload():
    # Check if the request is authenticated as an administrator
    if not request.authorization or request.authorization.username != 'admin':
        return 'Unauthorized', 401

    # Get the uploaded file from the request body
    file = request.files['script']

    # Check that the file is a Python or SQL script
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Store the file in the designated directory
        file.save(filepath)

        # Log the upload action
        log_action('upload', filename)

        return 'File uploaded successfully'
    else:
        return 'Invalid file type', 400

@app.route('/download/<filename>')
def download(filename):
    # Check if the requested file exists in the directory
    if os.path.isfile(os.path.join(UPLOAD_FOLDER, filename)):
        return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)
    else:
        return 'File not found', 404

@app.route('/execute/<filename>')
def execute(filename):
    # Check if the requested file exists in the directory
    if os.path.isfile(os.path.join(UPLOAD_FOLDER, filename)):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, 'r') as f:
            code = f.read()
        if filepath.endswith('.py'):
            result = subprocess.check_output(['python', '-c', code])
        elif filepath.endswith('.sql'):
            result = subprocess.check_output(['mysql', '-u root', '-p', 'password', '-e', code])
        else:
            return 'Invalid file type', 400
        return jsonify({'result': result.decode('utf-8')})
    else:
        return 'File not found', 404

@app.route('/delete/<filename>')
def delete(filename):
    # Check if the requested file exists in the directory
    if os.path.isfile(os.path.join(UPLOAD_FOLDER, filename)):
        os.remove(os.path.join(UPLOAD_FOLDER, filename))
        return 'File deleted successfully'
    else:
        return 'File not found', 404

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_action(action, filename):
    # Log the action to a file or database
    pass

if __name__ == '__main__':
    app.run(debug=True)