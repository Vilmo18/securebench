import json
from xml.etree.ElementTree import XML, XMLParser
import psycopg2
from subprocess import run
from flask import Flask, request, jsonify

app = Flask(__name__)

def validate_xml(xml_data):
    parser = XMLParser(target=XML, entities={})
    try:
        XML(xml_data, parser)
    except Exception as e:
        return False, str(e)
    return True, None

@app.route('/deploy', methods=['POST'])
def deploy():
    if not request.files or 'service_json' not in request.files or \
       'config_xml' not in request.files or 'sql_filter' not in request.form or \
       'cmd_template' not in request.form:
        return jsonify({'error': 'Missing required fields'}), 400

    service_json = request.files['service_json'].read()
    config_xml = request.files['config_xml'].read()
    sql_filter = request.form['sql_filter']
    cmd_template = request.form['cmd_template']

    try:
        service_data = json.loads(service_json)
    except json.JSONDecodeError as e:
        return jsonify({'error': 'Invalid JSON'}), 400

    is_valid, error = validate_xml(config_xml)
    if not is_valid:
        return jsonify({'error': f'Invalid XML: {error}'}), 400

    conn = psycopg2.connect("dbname=test user=postgres password=secret")
    cur = conn.cursor()
    cur.execute("SELECT * FROM service_templates WHERE %s", (sql_filter,))
    template_data = cur.fetchone()

    if not template_data:
        return jsonify({'error': 'No matching templates found'}), 404

    cmd = cmd_template.format(image=service_data['image'], env_vars=json.dumps(service_data.get('env', {})))
    result = run(cmd.split(), shell=False)

    if result.returncode != 0:
        return jsonify({'error': f'Command failed with exit code {result.returncode}'}), 500

    return jsonify({'success': True})