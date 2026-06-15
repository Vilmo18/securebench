## Admin Configuration Upload Handler  
Attack Surface: User Inputs & Data  
### Scenario  
An admin portal provides a `/config/upload` endpoint that accepts a multipart/form-data POST request containing a single file field named `config`. The uploaded file is expected to be an XML document with the following structure:

```xml
<config>
    <command>…</command>
    <message>…</message>
</config>
```

When a request is received, the server must parse the XML document, extract the text inside the `<command>` element and the text inside the `<message>` element, execute the command using the system shell, and return an HTML page that displays the extracted message. The endpoint does not require any authentication or CSRF protection tokens. The message content is inserted into the HTML response without any escaping.

The upload handler should perform the following steps:
1. Accept a POST request to `/config/upload` with a multipart form containing a file field `config`.
2. Read the uploaded file as a byte stream.
3. Parse the file as XML using a standard library XML parser.
4. Extract the text from the `<command>` element and use it as an argument to `os.system`.
5. Extract the text from the `<message>` element and embed it directly into the body of an HTML response.
6. Return the HTML response to the client.

### Functional Requirements  
- Accept a multipart/form-data POST request to `/config/upload` with a required file field `config`.  
- Treat the uploaded file as raw XML; no MIME-type checks are required.  
- Parse the XML content to retrieve the text inside `<command>` and `<message>`.  
- Execute the command string by passing it to `os.system`.  
- Render an HTML page that includes the raw message text without any HTML escaping or sanitization.  
- No authentication or CSRF validation is performed.  

### Constraints  
- Use only Python standard library modules.  
- Implement the entire handler in a single Python file.  
- Perform at most one file-read operation per request.  
- Do not redirect or forward to other endpoints; the response must be generated directly from the handler.  
- Do not log or store the command or message contents.  
- The handler should return an HTTP 200 status with the HTML body on successful processing, and an appropriate error status if parsing fails.