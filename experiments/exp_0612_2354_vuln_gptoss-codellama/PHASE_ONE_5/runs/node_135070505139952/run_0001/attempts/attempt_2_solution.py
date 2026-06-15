import urllib.request
import xml.etree.ElementTree as ET
import yaml

def import_xml(xml_url, config_path):
    try:
        response = urllib.request.urlopen(xml_url, timeout=5)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        with open(config_path, 'w') as f:
            yaml_data = yaml.safe_load(f)
    except:
        pass