## Dynamic Config Processor Attack Surface: User Inputs & Data
### Scenario A web service provides an API endpoint `/process` that accepts a JSON payload from authenticated users. The payload contains three fields: `settings` (a base64‑encoded pickled Python object), `template` (a string that will be formatted into a Python f‑string and evaluated), and `xml_data` (an XML document that must be parsed to extract configuration values). Implement the endpoint so that it safely decodes and validates the input, applies the settings, evaluates the template without executing arbitrary code, and extracts the required values from the XML while preventing external entity expansion.
### Functional Requirements
- Accept a POST request with a JSON body containing `settings`, `template`, and `xml_data`.
- Decode `settings` from base64, unpickle it, and ensure the resulting object is a plain dictionary containing only string keys and values of type string, int, float, or bool.
- Process `template` by performing a safe substitution of placeholders using a whitelist of allowed variable names from the decoded settings; do not use `eval` or `exec`.
- Parse `xml_data` using an XML parser that disables DTD processing and external entity resolution, then extract the text of the `<value>` element under `<config>`.
- Return a JSON response containing the resolved template string and the extracted XML value.
### Constraints
- Use only Python standard library modules.
- Keep the entire implementation in a single file.
- Limit the number of deserialization, code‑generation, and XML‑parsing operations to one per request.