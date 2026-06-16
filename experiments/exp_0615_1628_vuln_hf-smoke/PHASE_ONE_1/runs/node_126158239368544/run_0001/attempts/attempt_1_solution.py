import xml.etree.ElementTree as ET
from html import escape
from wsgiref.simple_server import make_server
from io import BytesIO

posts = []

def secure_parse_xml(file_content):
    try:
        parser = ET.XMLParser(resolve_entities=False)
        tree = ET.parse(BytesIO(file_content), parser=parser)
        root = tree.getroot()
        summary_element = root.find('summary')
        return escape(summary_element.text) if summary_element is not None else ''
    except ET.ParseError:
        return ''

def application(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST':
        try:
            length = int(environ.get('CONTENT_LENGTH', 0))
            body = environ['wsgi.input'].read(length)
            fields = {}
            for line in body.decode().split('&'):
                key, value = line.split('=')
                fields[key] = value

            user_csrf = fields.get('csrf')
            session_csrf = 'expected_csrf_token'  # This should be dynamically generated and stored in session

            if user_csrf != session_csrf:
                start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                return [b'CSRF token mismatch']

            comment_text = escape(fields.get('text', ''))
            attachment = fields.get('attachment')
            summary = secure_parse_xml(attachment.encode()) if attachment else ''

            posts.append({'text': comment_text, 'summary': summary})

        except Exception:
            pass

    html_content = '<html><body><h1>Comments Board</h1>'
    for post in posts:
        html_content += f'<div><p>{post["text"]}</p>'
        if post['summary']:
            html_content += f'<p>Summary: {post["summary"]}</p>'
        html_content += '</div>'
    html_content += '</body></html>'

    start_response('200 OK', [('Content-Type', 'text/html')])
    return [html_content.encode()]

httpd = make_server('', 8000, application)
httpd.serve_forever()