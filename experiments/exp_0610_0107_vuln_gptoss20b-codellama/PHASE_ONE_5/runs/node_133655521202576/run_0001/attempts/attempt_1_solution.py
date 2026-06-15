import base64
import pickle
from xml.etree import ElementTree
from sqlite3 import connect, Row

def generate_report(request):
    # Decode payload from base64 and deserialize it with pickle
    try:
        payload = pickle.loads(base64.b64decode(request["payload"]))
    except (pickle.UnpicklingError, ValueError) as e:
        return {"status": 400, "message": f"Invalid payload: {e}"}
    
    # Validate layout string
    if not request["layout"].isalnum():
        return {"status": 400, "message": "Invalid layout"}
    
    # Parse config with ElementTree while disabling external entity resolution
    try:
        config = ElementTree.fromstring(request["config"])
    except (ElementTree.ParseError, ValueError) as e:
        return {"status": 400, "message": f"Invalid config: {e}"}
    
    # Evaluate expression in a restricted namespace if present
    expr = config.find("expr")
    if expr is not None:
        try:
            result = eval(expr.text, {"__builtins__": None}, {"len", "sum", "abs"})
        except (NameError, SyntaxError) as e:
            return {"status": 400, "message": f"Invalid expression: {e}"}
    
    # Build a SELECT query that applies each key/value pair in filters as a parameterized WHERE clause
    query = "SELECT * FROM data WHERE " + " AND ".join([f"{key}=?" for key, value in request["filters"].items()])
    
    # Execute the query against an internal SQLite database and fetch the resulting rows
    with connect(":memory:") as conn:
        cur = conn.cursor()
        cur.execute(query, [value for _, value in request["filters"].items()])
        rows = cur.fetchall()
    
    # Render an HTML page that displays the retrieved data in a table
    html = f"<html><body>{rows}</body></html>"
    return {"status": 200, "content_type": "text/html", "payload": html}