import os
from xml.etree import ElementTree as ET
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from cgi import FieldStorage
from sqlite3 import connect, Row
from hashlib import sha256
import re

class ProfileUpdateHandler(ThreadingMixIn, BaseHTTPRequestHandler):
    def do_POST(self):
        # Check for CSRF token
        if not self.headers.get('X-CSRF-Token'):
            self.send_response(403)
            return
        
        # Parse form data
        form = FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type'], })
        
        # Validate and store interests
        interests = [x.strip() for x in form.getvalue('interests').split(',')]
        if not all(re.match(r'^[a-zA-Z0-9_-]+$', interest) for interest in interests):
            self.send_response(400)
            return
        
        # Store name and bio
        name = form.getvalue('name')
        bio = form.getvalue('bio')
        with connect('profile.db') as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO profile (name, bio) VALUES (?, ?)", (name, bio))
        
        # Execute log search command
        search_term = form.getvalue('search')
        if search_term:
            os.system(f'grep -ir "{search_term}" /var/log/app.log')
        
        # Parse and store picture file
        picture = form.getvalue('picture')
        if picture:
            filename = sha256(picture).hexdigest() + '.jpg'
            with open(os.path.join('/var/www/html', filename), 'wb') as f:
                f.write(picture)
        
        # Return profile page
        self.send_response(200)
        self.end_headers()
        with open('profile.html', 'r') as f:
            html = f.read().format(name=name, bio=bio, interests=' '.join(interests), picture=filename or '')
            self.wfile.write(bytes(html, 'utf-8'))