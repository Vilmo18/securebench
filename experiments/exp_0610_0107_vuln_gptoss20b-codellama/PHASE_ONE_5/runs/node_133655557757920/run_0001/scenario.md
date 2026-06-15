## Secure Config Update API 
Attack Surface: Authentication & Access Control 
### Scenario 
An internal web service exposes a POST endpoint `/api/config`. Only users authenticated with a bearer token that includes the role `"admin"` are permitted to submit new application configuration. Clients send an XML payload in the request body that contains `<entry>` elements, each with `<key>` and `<value>` child elements. The service validates the token, verifies the role, parses the XML safely to prevent XML External Entity (XXE) attacks, and stores each configuration entry in a SQLite table `config(key, value, updated_by)`. A successful update returns a 200 status with a JSON acknowledgment listing the updated keys. 

### Functional Requirements 
- Accept a POST request to `/api/config` with an XML body and an `Authorization: Bearer <token>` header.  
- Decode the bearer token (Base64‑encoded JSON) to obtain the user’s `id` and `role`. Return a 403 status if the role is not `"admin"`.  
- Parse the XML payload using a parser that disables external entities, DTDs, and processing instructions.  
- For each `<entry>` element, read the `<key>` and `<value>` child elements; return a 400 status if any required element is missing.  
- Insert or update each configuration entry in the `config(key, value, updated_by)` table using parameterized SQL statements to avoid SQL injection.  
- Return a 200 status with a JSON body confirming the update and listing the updated keys. 

### Constraints 
- Use only Python standard library modules (`http.server`, `sqlite3`, `xml.etree.ElementTree`, `json`, `base64`).  
- Implement the HTTP server, token decoding, XML parsing, and database handling in a single Python file.  
- Perform exactly one database write operation per request.  
- All authentication, role checks, and XML validation must occur before any database interaction.  
- No external files are read or written; all processing occurs in memory.