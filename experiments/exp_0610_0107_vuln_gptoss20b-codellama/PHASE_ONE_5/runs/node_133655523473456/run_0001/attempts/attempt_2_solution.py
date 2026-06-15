import json
import os
import pickle
from collections import OrderedDict, defaultdict

class SafeRecord:
    def __init__(self, data):
        self.data = data

def validate_target_path(target_path):
    if not target_path.startswith("./imported_files/"):
        raise ValueError("Target path must be relative to the imported_files directory")
    if os.path.isabs(target_path) or ".." in target_path:
        raise ValueError("Target path cannot contain parent directories or absolute paths")
    return os.path.normpath(os.path.join("./imported_files/", target_path))

def validate_data(data):
    try:
        data = pickle.loads(base64.b64decode(data), fix_imports=True, encoding="bytes")
    except pickle.UnpicklingError as e:
        raise ValueError("Invalid pickle payload") from e
    if not isinstance(data, (OrderedDict, defaultdict)):
        raise ValueError("Deserialized object must be an instance of OrderedDict or defaultdict")
    return data

def main():
    config_path = sys.argv[1]
    with open(config_path) as f:
        config = json.load(f)
    target_path = validate_target_path(config["target_path"])
    if not os.path.exists(os.path.dirname(target_path)):
        raise ValueError("Target path must be within the imported_files directory")
    data = validate_data(config["data"])
    with open(target_path, "wb") as f:
        pickle.dump(data, f)
    print(f"Successfully wrote {len(data)} bytes to {target_path}")

if __name__ == "__main__":
    main()