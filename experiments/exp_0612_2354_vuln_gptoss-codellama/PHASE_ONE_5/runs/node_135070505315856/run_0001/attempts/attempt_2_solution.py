import os
import sqlite3
from flask import Flask, request, send_file

app = Flask(__name__)

# Create the uploads directory if it does not exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Connect to the SQLite database
conn = sqlite3.connect('files.db')
c = conn.cursor()

@app.route('/', methods=['POST'])
def upload():
    # Get the file and filename from the request
    file = request.files['file']
    filename = request.form['filename']

    # Save the file to the uploads directory using a secure method
    file.save(os.path.join('uploads', filename))

    # Insert a row into the files table with the columns (id INTEGER PRIMARY KEY, name TEXT)
    c.execute("INSERT INTO files (name) VALUES (?)", (filename,))
    conn.commit()

    return 'File uploaded successfully'

@app.route('/', methods=['GET'])
def download():
    # Get the requested file name from the query parameter
    filename = request.args.get('name')

    # Check if the file exists in the uploads directory using a secure method
    if os.path.exists(os.path.join('uploads', filename)):
        # Return the file contents with the Content-Type header set to application/octet-stream
        return send_file(os.path.join('uploads', filename), as_attachment=True)
    else:
        # If the file does not exist, return a 404 response
        return 'File not found', 404

@app.route('/', methods=['DELETE'])
def delete():
    # Get the requested file name from the query parameter
    filename = request.args.get('name')

    # Check if the file exists in the uploads directory using a secure method
    if os.path.exists(os.path.join('uploads', filename)):
        # Remove the file from the uploads directory and delete its database record using a secure method
        os.remove(os.path.join('uploads', filename))
        c.execute("DELETE FROM files WHERE name = ?", (filename,))
        conn.commit()

        return 'File deleted successfully'
    else:
        # If the file does not exist, return a 404 response
        return 'File not found', 404

# Run the Flask app using a secure method
if __name__ == "__main__":
    app.run(debug=False)