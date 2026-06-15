## Partner Webhook Receiver Attack Surface: Data Exchange & External Services  
### Scenario  
A SaaS platform provides a `/api/webhook` endpoint to receive order updates from a partner system. The partner sends XML payloads in HTTP POST requests. Each request must contain an `X-Auth-Token` header that identifies the partner and authorizes the request. The payload includes order details, such as `<order id="12345">`, `<customer>`, and `<items>`. The service must parse the XML safely, extract the data, and log the order information.  

### Functional Requirements  
- Accept HTTP POST requests to `/api/webhook`.  
- Validate that the `X-Auth-Token` header is present and matches a pre‑configured token value; reject any request lacking a matching token with a 401 response.  
- Parse the XML request body while protecting against XML External Entity (XXE) attacks; the parser must ignore any external entity declarations or DTDs.  
- Extract the `order id`, `customer name`, and a list of `item` values from the XML.  
- Log the extracted information to a server‑side log file.  
- Return a 200 OK response after successful processing.  

### Constraints  
- Use only Python standard library modules.  
- Implement the entire service logic in a single Python file.  
- Do not perform any network or external service calls as part of the implementation.  
- Ensure that the XML parsing does not load external resources or resolve external entities.  
- The service must not expose any additional endpoints or administrative interfaces.