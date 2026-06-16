from flask import Flask, request, jsonify, render_template_string, abort
import json

app = Flask(__name__)

# Whitelist of allowed templates
ALLOWED_TEMPLATES = {
    'summary': '<html><body><h1>Summary Report</h1>{{ data }}</body></html>',
    'detailed': '<html><body><h1>Detailed Report</h1>{{ data }}</body></html>'
}

# Simulated database
REPORT_DATABASE = {
    1: {'title': 'Report 1', 'content': 'This is the content of report 1'},
    2: {'title': 'Report 2', 'content': 'This is the content of report 2'}
}

def get_report(report_id, filters):
    # Simulate a database query using parameterized approach
    if report_id not in REPORT_DATABASE:
        return None
    report = REPORT_DATABASE[report_id]
    # Apply filters (for demonstration, we assume filters are directly applicable)
    for key, value in filters.items():
        if key in report and report[key] != value:
            return None
    return report

@app.route('/view_report')
def view_report():
    try:
        report_id = int(request.args.get('report_id'))
    except (TypeError, ValueError):
        abort(400, description="Invalid report_id parameter")

    filter_param = request.args.get('filter', '{}')
    try:
        filters = json.loads(filter_param)
    except json.JSONDecodeError:
        abort(400, description="Invalid filter parameter")

    view_param = request.args.get('view')
    if view_param not in ALLOWED_TEMPLATES:
        abort(400, description="Invalid view parameter")

    report_data = get_report(report_id, filters)
    if not report_data:
        abort(404, description="Report not found")

    template = ALLOWED_TEMPLATES[view_param]
    html_output = render_template_string(template, data=report_data)
    return html_output, 200, {'Content-Type': 'text/html'}

if __name__ == '__main__':
    app.run(debug=False)