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
            result = ast.literal_eval(expr.text)
        except (NameError, SyntaxError) as e:
            return {"status": 400, "message": f"Invalid expression: {e}"}
    
    # Build SQL query from config
    try:
        sql = build_sql_query(config)
    except (ValueError, KeyError) as e:
        return {"status": 400, "message": f"Invalid configuration: {e}"}
    
    # Execute SQL query and retrieve results
    try:
        cursor = connect().cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
    except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
        return {"status": 500, "message": f"Internal server error: {e}"}
    
    # Build response object
    response = {"status": 200, "data": []}
    for row in rows:
        response["data"].append({"id": row[0], "name": row[1]})
    
    return response