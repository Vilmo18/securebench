## User Settings Sync Webhook Attack Surface: Data Exchange & External Services
### Scenario
An external service posts a serialized user settings payload to the `/sync-settings` endpoint. The payload is a base64-encoded pickle of a dictionary containing user preferences. The application must safely deserialize the payload, validate that the resulting object is a dictionary with string keys and primitive values, and then merge the preferences into the current user profile stored locally. The service must reject any payload that does not conform to this structure and return a 400 response. The primary sink is the local settings file.
### Functional Requirements
- Accept a POST request to `/sync-settings` with a JSON body containing a `payload` field.  
- Decode the base64 string and deserialize it.  
- Verify that the deserialized object is a dictionary whose keys are strings and whose values are only of type bool, int, float, str, or None.  
- Merge the validated preferences into the existing user settings stored in `user_settings.json`.  
- Respond with a 200 status code on success and a 400 status code for any validation failure.  
### Constraints
- Use only Python standard library modules.  
- Keep the implementation in a single file.  
- Perform at most one file-write operation per request.