import json
import sqlite3
import re
import hmac
import hashlib
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote
from pathlib import Path

CSRF_SECRET = b'your_preconfigured_csrf_secret'
RECEIPTS_DIR = Path('receipts/')
DATABASE_PATH = 'payments.db'

def secure_compare(val1, val2):
    return hmac.compare_digest(val1, val2)

def validate_csrf_token(request_headers):
    csrf_token = request_headers.get('X-CSRF-Token')
    if not csrf_token or not secure_compare(csrf_token.encode(), CSRF_SECRET):
        return False
    return True

def parse_payment_data(payload):
    try:
        data = json.loads(payload)
        user_id = data.get('user_id')
        amount = data.get('amount')
        receipt_path = data.get('receipt_path')

        if not isinstance(user_id, int) or user_id <= 0:
            return None, "Invalid user_id"

        if not isinstance(amount, str) or not re.match(r'^\d+(\.\d{1,2})?$', amount):
            return None, "Invalid amount"

        if receipt_path:
            receipt_path = unquote(receipt_path)
            if (
                os.path.isabs(receipt_path) or
                '..' in receipt_path.split(os.sep) or
                '\x00' in receipt_path
            ):
                return None, "Unsafe receipt_path"
            receipt_path = RECEIPTS_DIR / receipt_path
            try:
                receipt_path.resolve().relative_to(RECEIPTS_DIR)
            except ValueError:
                return None, "Receipt path resolves outside the designated directory"

        return (user_id, amount, str(receipt_path) if receipt_path else None), None
    except json.JSONDecodeError:
        return None, "Malformed JSON"

def create_payment_record(user_id, amount, receipt_path):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount TEXT NOT NULL,
            receipt_path TEXT
        )
    ''')
    cursor.execute('INSERT INTO payments (user_id, amount, receipt_path) VALUES (?, ?, ?)', (user_id, amount, receipt_path))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id

class PaymentHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/api/payments':
            self.send_error(404, "Not Found")
            return

        if not validate_csrf_token(self.headers):
            self.send_response(403)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid CSRF token"}).encode())
            self.log_message(f"Request ID: {self.client_address[1]} - Client: {self.client_address[0]} - Outcome: Invalid CSRF token")
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)

        parsed_data, error_message = parse_payment_data(post_data)
        if error_message:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": error_message}).encode())
            self.log_message(f"Request ID: {self.client_address[1]} - Client: {self.client_address[0]} - Outcome: {error_message}")
            return

        user_id, amount, receipt_path = parsed_data
        try:
            payment_id = create_payment_record(user_id, amount, receipt_path)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "payment_id": payment_id}).encode())
            self.log_message(f"Request ID: {self.client_address[1]} - Client: {self.client_address[0]} - Outcome: Success")
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Database error"}).encode())
            self.log_message(f"Request ID: {self.client_address[1]} - Client: {self.client_address[0]} - Outcome: Database error - {str(e)}")

def run(server_class=HTTPServer, handler_class=PaymentHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()