## User Dashboard Renderer  
Attack Surface: Web Outputs & Rendering  

### Scenario  
A web application provides a `/dashboard` page for logged‑in users. The page accepts three optional query parameters:  

* `search` – a free‑form string used to filter the user's recent activity records stored in a relational database.  
* `note` – a short text that the user can submit to be displayed as a personal note on the dashboard.  
* `xml_source` – a URL pointing to an XML document containing a `<summary>` element that should be fetched, parsed, and the summary text rendered on the page.  

The handler must query the database for activity rows matching the `search` term, render the result set in an HTML table, embed the escaped `note` beneath the table, and include the extracted XML summary below the note. All output is returned as an HTML page to the browser.

### Functional Requirements  
- Accept the `search`, `note`, and `xml_source` query parameters from the HTTP GET request.  
- Execute a database query that selects activity records where the description contains the `search` term.  
- Render the resulting records in an HTML `<table>`.  
- Display the `note` value on the page exactly as entered by the user, but without allowing any executable markup.  
- Retrieve the XML document from the supplied `xml_source` URL, parse it safely, extract the text content of the first `<summary>` element, and render that text on the page.  
- Return a well‑formed HTML page with appropriate `Content-Type: text/html` header.  

### Constraints  
- Use only Python standard library modules (e.g., `sqlite3`, `html`, `xml.etree.ElementTree`, `urllib.request`).  
- Keep the entire implementation within a single Python file, sized between 20 and 80 lines of code.  
- Perform at most one database query and one XML fetch per request.  
- Ensure that all rendered content does not unintentionally execute scripts or load external entities.