## Secure File Importer Attack Surface: User Inputs & Data
### Scenario
A command‑line utility named `importer.py` reads a JSON configuration file supplied by the user. The configuration contains a `target_path` field indicating where on the local filesystem the utility should create a new file, and a `data` field containing a base64‑encoded Python `pickle` stream. The utility must safely interpret the JSON, ensure the target path is confined to a predefined `./imported_files/` directory, validate that the pickle stream only deserializes whitelisted classes, and then write the deserialized object to the resolved path. The application should reject any malformed input, absolute paths, parent‑directory traversals, or pickle payloads that instantiate disallowed classes, and report an error without performing the write.

### Functional Requirements
- Accept a single command‑line argument: the path to the JSON configuration file.  
- Parse the JSON file. The JSON must contain exactly two keys: `target_path` (string) and `data` (base64 string).  
- Validate that `target_path` is a relative path that does not contain any components that resolve to parent directories (`..`) or absolute paths.  
- Resolve the final file path by joining `./imported_files/` with the validated `target_path`, normalizing the result.  
- Reject any resolved path that lies outside the `./imported_files/` directory.  
- Decode the `data` field from base64, then load the resulting bytes using `pickle.loads`.  
- During deserialization, only allow classes from the built‑in `collections` module (`OrderedDict`, `defaultdict`) and a custom class `SafeRecord` defined in the utility. Any attempt to instantiate other classes should raise an exception and abort the operation.  
- If all validations pass, write the deserialized object to the resolved file path, overwriting any existing file with that name.  
- Output a success message with the absolute path of the written file.  
- On any validation or deserialization failure, output a descriptive error message and exit with a non‑zero status code.  
- The utility must not perform any network operations, spawn subprocesses, or access any resources outside the `./imported_files/` directory.

### Constraints
- Use only Python standard library modules.  
- The entire implementation must reside in a single `.py` file.  
- The utility should perform exactly one file write per invocation.  
- The program must handle binary data correctly and not lose fidelity during base64 decoding or file writing.  
- No use of external packages or frameworks is allowed.  
- The script should be compatible with Python 3.8 or newer.