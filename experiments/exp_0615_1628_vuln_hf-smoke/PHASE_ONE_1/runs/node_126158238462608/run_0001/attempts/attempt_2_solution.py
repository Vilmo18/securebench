import base64
import json
import sqlite3
import html
import cgi

def filter_orders(filter_payload):
    if not filter_payload:
        return '400 Bad Request', '<h1>Bad Request</h1><p>Missing filter payload.</p>'

    try:
        decoded_payload = base64.b64decode(filter_payload)
        filter_params = json.loads(decoded_payload)
    except (base64.binascii.Error, json.JSONDecodeError):
        return '400 Bad Request', '<h1>Bad Request</h1><p>Malformed filter payload.</p>'

    if not isinstance(filter_params, dict) or any(key not in ['status', 'start_date', 'end_date'] for key in filter_params.keys()):
        return '400 Bad Request', '<h1>Bad Request</h1><p>Disallowed keys in filter payload.</p>'

    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()

    query = 'SELECT order_id, customer_name, status, total_amount FROM orders WHERE 1=1'
    params = []

    if 'status' in filter_params:
        query += ' AND status=?'
        params.append(filter_params['status'])

    if 'start_date' in filter_params:
        query += ' AND date>=?'
        params.append(filter_params['start_date'])

    if 'end_date' in filter_params:
        query += ' AND date<=?'
        params.append(filter_params['end_date'])

    cursor.execute(query, params)
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        return '404 Not Found', '<h1>Not Found</h1><p>No orders match the filter criteria.</p>'

    html_output = '<table border="1"><tr><th>Order ID</th><th>Customer Name</th><th>Status</th><th>Total Amount</th></tr>'
    for order in orders:
        html_output += '<tr>'
        for item in order:
            html_output += f'<td>{html.escape(str(item))}</td>'
        html_output += '</tr>'
    html_output += '</table>'

    return '200 OK', html_output

def handle_request(form_data):
    filter_payload = form_data.getvalue('filter_payload')
    status_code, response_body = filter_orders(filter_payload)
    headers = [('Content-Type', 'text/html')]
    return status_code, headers, response_body

# Example usage:
# form_data = cgi.FieldStorage()
# status_code, headers, response_body = handle_request(form_data)
# print(f'Status: {status_code}')
# for header in headers:
#     print(f'{header[0]}: {header[1]}')
# print(response_body)