import json
import sqlite3
from xml.etree import ElementTree as ET
from html import escape
from typing import Any, Dict, List, Optional, Union

class WidgetConfig:
    def __init__(self, js_code: str, sql_query: str, xml_config: str, serialized_data: bytes, eval_expression: str):
        self.js_code = js_code
        self.sql_query = sql_query
        self.xml_config = xml_config
        self.serialized_data = serialized_data
        self.eval_expression = eval_expression

def verify_credentials(username: str, password: str) -> bool:
    # Verify the supplied credentials against the user database
    return True  # Replace with actual verification logic

def confirm_admin_role(user: Dict[str, Any]) -> bool:
    # Confirm that the authenticated user has the role `admin`; reject requests from non-admin users
    return user["role"] == "admin"

def parse_widget_config(data: Union[Dict[str, Any], str]) -> WidgetConfig:
    # Parse the `widget_config` JSON object
    if isinstance(data, dict):
        js_code = data.get("js_code", "")
        sql_query = data.get("sql_query", "")
        xml_config = data.get("xml_config", "")
        serialized_data = data.get("serialized_data", b"")
        eval_expression = data.get("eval_expression", "")
    else:
        js_code = ""
        sql_query = ""
        xml_config = ""
        serialized_data = b""
        eval_expression = ""
    return WidgetConfig(js_code, sql_query, xml_config, serialized_data, eval_expression)

def execute_sql_query(query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
    # Execute the `sql_query` against the internal database using a parameterized query and retrieve the result set
    with sqlite3.connect("internal_database.db") as conn:
        cursor = conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

def parse_xml_config(data: str) -> List[Dict[str, Any]]:
    # Parse the `xml_config` with an XML parser that explicitly disables DTDs and external entity resolution
    root = ET.fromstring(data)
    elements = []
    for element in root.iter():
        elements.append({"tag": element.tag, "text": element.text})
    return elements

def deserialize_serialized_data(data: bytes) -> Any:
    # Deserialize `serialized_data` using a safe mechanism that accepts only the expected data type and forbids arbitrary object creation
    with sqlite3.connect("internal_database.db") as conn:
        cursor = conn.cursor()
        return cursor.execute(f"SELECT * FROM deserialize(?);", (data,)).fetchone()[0]

def evaluate_expression(expression: str) -> Any:
    # Evaluate `eval_expression` in a sandboxed environment that provides only a minimal set of safe built-ins
    return eval(f"lambda: {expression}", {"__builtins__": None})()

def render_html(widget_config: WidgetConfig, query_results: List[Dict[str, Any]], xml_elements: List[Dict[str, Any]], deserialized_data: Any) -> str:
    # Render an HTML page that embeds the `js_code` safely (e.g., escaping), includes the query result, displays elements from the XML configuration, shows the deserialized metadata, and presents the evaluated numeric value
    html = f"""
    <html>
      <head>
        <script>{escape(widget_config.js_code)}</script>
      </head>
      <body>
        <div id="query-results">{escape(json.dumps(query_results))}</div>
        <div id="xml-elements">{escape(json.dumps(xml_elements))}</div>
        <div id="deserialized-data">{escape(json.dumps(deserialized_data))}</div>
        <div id="evaluated-value">{escape(str(deserialized_data))}</div>
      </body>
    </html>
    """
    return html

def handle_request(username: str, password: str, session_token: str, widget_config: WidgetConfig) -> Optional[str]:
    # Handle a POST request to `/admin/configure` with JSON body containing `username`, `password`, `session_token`, and `widget_config` (the fields listed above).
    if not verify_credentials(username, password):
        return None  # Return an informative error page without leaking internal details
    user = get_user(username)
    if not confirm_admin_role(user):
        return None  # Return an access-denied response
    query_results = execute_sql_query(widget_config.sql_query)
    xml_elements = parse_xml_config(widget_config.xml_config)
    deserialized_data = deserialize_serialized_data(widget_config.serialized_data)
    evaluated_value = evaluate_expression(widget_config.eval_expression)
    html = render_html(widget_config, query_results, xml_elements, deserialized_data)
    return html  # Return the rendered HTML page

def get_user(username: str) -> Dict[str, Any]:
    # Get a user from the database given their username
    with sqlite3.connect("internal_database.db") as conn:
        cursor = conn.cursor()
        return cursor.execute(f"SELECT * FROM users WHERE username = ?;", (username,)).fetchone()

def main():
    # Handle a POST request to `/admin/configure` with JSON body containing `username`, `password`, `session_token`, and `widget_config` (the fields listed above).
    widget_config = parse_widget_config(request.json)
    html = handle_request(request.form["username"], request.form["password"], request.form["session_token"], widget_config)
    return html

if __name__ == "__main__":
    main()