import sqlite3
from defusedxml import ElementTree as ET
from html import escape

def parse_xml(data):
    root = ET.fromstring(data, forbid_dtd=True, forbid_external=True)
    elements = []
    for element in root:
        elements.append({"name": element.attrib["name"], "value": element.text})
    return elements

def handle_request(request):
    if request.method == "POST":
        widget_data = parse_xml(request.body)
        # Do something with the data
        print(widget_data)
    else:
        return {"message": "Invalid request method"}, 400

if __name__ == "__main__":
    app = Flask(__name__)
    CORS(app)
    app.config["CORS_HEADERS"] = "Content-Type"
    app.register_blueprint(bp)
    app.run(debug=True)