import hashlib
import hmac
import json
import sqlite3

def verify_signature(request, secret):
    signature = request.headers.get('X-Signature')
    if not signature:
        return False
    computed_signature = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_signature, signature)

def process_request(request):
    if not verify_signature(request, secret):
        return 'Unauthorized', 401
    try:
        data = json.loads(request.body)
        service_id = data['service_id']
        event_type = data['event_type']
        payload = data['payload']
        received_at = datetime.datetime.utcnow()
        with sqlite3.connect('events.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO events (service_id, event_type, payload, received_at) VALUES (?, ?, ?, ?)", (service_id, event_type, payload, received_at))
        return 'OK', 200
    except Exception:
        return 'Internal Server Error', 500

if __name__ == '__main__':
    import http.server
    secret = 'mysecret'
    with http.server.HTTPServer(('localhost', 8000), process_request) as httpd:
        print(f'Serving on {httpd.server_address}...')
        httpd.serve_forever()