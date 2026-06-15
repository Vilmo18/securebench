## Dynamic Data Processing API Attack Surface: User Inputs & Data
### Scenario
A web service exposes a `/process` POST endpoint that accepts a JSON payload from clients. The payload contains two fields:  
- `payload` – a base64‑encoded string representing a pickled Python object.  
- `operation` – a string containing arbitrary Python code that should run on the deserialized object.  

The endpoint is only intended for authenticated users. The service must validate the request, safely deserialize the data, execute the supplied code in a restricted environment, and return the result.  
The design must enforce authentication, prevent unsafe deserialization, and limit code execution to a controlled subset of the standard library.

### Functional Requirements
- Accept a `POST /process` request with a JSON body containing `payload` and `operation` fields.  
- Verify the presence of an `Authorization` header; reject the request with a 401 response if the header is missing or invalid.  
- Base64‑decode the `payload` field and deserialize it using `pickle`. Only allow deserialization of objects that are instances of the `dict` or `list` types; reject all others with a 400 response.  
- Compile the `operation` string into a code object. Execute the compiled code in a sandboxed environment where the only global names available are `payload`, `json`, and `math`; all built‑ins and other modules must be inaccessible.  
- Capture the value of the variable `result` produced by the executed code and return it as a JSON response under the key `result`.  
- For any request that fails validation, decoding, deserialization, or execution, return a descriptive error message with an appropriate HTTP status code.

### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single Python file.  
- Perform at most one pickled deserialization per request.  
- The sandbox must prevent the executed code from reading or writing to the filesystem or initiating network connections.  
- The solution should be straightforward to test without external services.