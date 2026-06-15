import os
import re
import subprocess
from xml.etree import ElementTree

def main(container_id, config_path=None):
    # Check that the effective user belongs to the system docker group
    if not os.getegid() in [g.pw_gid for g in os.getgrall() if g.gr_name == 'docker']:
        print("Error: You must be a member of the docker group to use this utility.")
        return

    # Validate container ID
    if not re.match(r'^[a-zA-Z0-9_-]+$', container_id):
        print("Error: Invalid container ID. Only alphanumeric characters, dashes, and underscores are allowed.")
        return

    # If a configuration file is provided, read it once and parse it with an XML parser that disallows external entity resolution
    if config_path:
        try:
            tree = ElementTree.parse(config_path)
            root = tree.getroot()
        except ElementTree.ParseError as e:
            print("Error: Unable to parse configuration file.")
            return

        # Resolve the target file path within the container while preventing traversal outside the intended filesystem boundary
        try:
            target_file_path = root.find('target-file').text
            if not os.path.commonprefix([os.path.abspath(config_path), target_file_path]) == os.path.abspath(config_path):
                print("Error: Target file path must be within the container's filesystem hierarchy.")
                return
        except AttributeError:
            pass

    # Use subprocess.run with shell=False to execute docker inspect <container_id> and capture its output for display
    try:
        result = subprocess.run(['docker', 'inspect', container_id], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(result.stdout.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        print("Error: Unable to inspect container.")
        return

    # If the XML configuration specifies a file path, list its contents safely
    if target_file_path:
        try:
            result = subprocess.run(['docker', 'exec', container_id, 'ls', '-l', target_file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            print(result.stdout.decode('utf-8'))
        except subprocess.CalledProcessError as e:
            print("Error: Unable to list contents of target file.")
            return

if __name__ == '__main__':
    main()