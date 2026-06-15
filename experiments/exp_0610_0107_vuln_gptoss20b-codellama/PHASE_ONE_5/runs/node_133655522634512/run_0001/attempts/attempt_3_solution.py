import cgi
import html
from xml.etree import ElementTree as ET
from base64 import b64decode
from pickle import loads

def parse_menu(xml):
    root = ET.fromstring(xml)
    items = []
    for item in root.findall('item'):
        title = item.findtext('title')
        data = item.findtext('data')
        if not (title and data):
            continue
        try:
            icon, order = loads(b64decode(data))['icon'], loads(b64decode(data))['order']
        except (KeyError, ValueError):
            continue
        items.append((title, icon, order))
    return items

def render_menu(items):
    html = '<h3>Menu</h3>'
    for title, icon, order in sorted(items, key=lambda x: x[2]):
        html += f'<h3>{html.escape(title)}</h3>'
        if icon:
            html += f'<img src="{icon}">'
    return html

def handle_request():
    form = cgi.FieldStorage()
    xml = form.getvalue('menu')
    if not xml or len(xml) > 1024 * 1024:
        return 'Invalid menu file. Please check the format.'
    try:
        items = parse_menu(xml)
    except ET.ParseError as e:
        return f'Invalid XML: {e}'
    html = render_menu(items)
    return html