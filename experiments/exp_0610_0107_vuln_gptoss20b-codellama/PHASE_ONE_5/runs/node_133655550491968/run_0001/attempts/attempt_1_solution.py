import xml.etree.ElementTree as ET
import sqlite3
from http import HTTPStatus

def parse_xml(config_xml):
    tree = ET.parse(config_xml)
    root = tree.getroot()
    category_id = root.find("category_id").text
    return category_id

def query_database(db, status, category_id):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category_id=? AND status=?", (category_id, status))
    results = c.fetchall()
    return results

def handle_request(config_xml, status):
    try:
        category_id = parse_xml(config_xml)
        results = query_database("products.db", status, category_id)
        return HTTPStatus.OK, {"results": results}
    except (ET.ParseError, sqlite3.OperationalError):
        return HTTPStatus.BAD_REQUEST, {}