import sqlite3
from html import escape
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from xml.etree.ElementTree import fromstring
from defusedxml.elementtree import fromstring as safe_fromstring

def dashboard_handler(request):
    search = request.get('search', '')  # Free-form string for filtering activity records
    note = request.get('note', '')      # Personal note to be displayed on the dashboard
    xml_source = request.get('xml_source', '')  # URL pointing to an XML document

    conn = sqlite3.connect('user_activity.db')
    cursor = conn.cursor()

    query = "SELECT * FROM activity WHERE description LIKE ?"
    cursor.execute(query, ('%' + search + '%',))
    rows = cursor.fetchall()
    conn.close()

    html_output = '<table border="1">\n'
    for row in rows:
        html_output += f'<tr><td>{escape(str(row))}</td></tr>\n'
    html_output += '</table>\n'

    if note:
        html_output += f'<p>Note: {escape(note)}</p>\n'

    if xml_source:
        try:
            parsed_url = urlparse(xml_source)
            if parsed_url.scheme not in ('http', 'https'):
                raise ValueError("Unsupported URL scheme")
            req = Request(xml_source, method='GET')
            with urlopen(req) as response:
                xml_content = response.read()
                root = safe_fromstring(xml_content)
                summary = root.find('summary').text
                html_output += f'<p>Summary: {escape(summary)}</p>\n'
        except Exception as e:
            html_output += f'<p>Error fetching XML: {escape(str(e))}</p>\n'

    return [200, {'Content-Type': 'text/html'}, [html_output.encode('utf-8')]]

# Example request dictionary for testing
request = {
    'search': '',
    'note': '<script>alert("XSS")</script>',
    'xml_source': 'http://example.com/data.xml'
}

response = dashboard_handler(request)
print(response[2][0].decode('utf-8'))