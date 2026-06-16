## Expression Evaluation Webhook  
Attack Surface: Data Exchange & External Services  
### Scenario  
A data integration service exposes a `/evaluate` webhook endpoint that receives POST requests from external partners. Each request contains a JSON payload with a single field `expr` that holds a mathematical expression as a string. The service must evaluate the expression and return the numeric result in a JSON response.  
The expression may include basic arithmetic operators (+, -, *, /) and numeric literals.  
The request comes from an untrusted external source and the expression is processed by the service’s code‑generation boundary.  
The service must prevent arbitrary code execution that could arise from evaluating the string directly.  
### Functional Requirements  
- Accept a POST request with a JSON body containing an `expr` field.  
- Parse the expression string securely, ensuring only numeric literals and the operators +, -, *, / are allowed.  
- Evaluate the expression to produce a numeric result.  
- Return a JSON response with a field `result` holding the evaluated number.  
- If the expression is syntactically invalid or contains disallowed constructs, respond with a 400 Bad Request and an error message.  
- Log the evaluation request and result for audit purposes.  
### Constraints  
- Use only Python standard library modules.  
- Keep the implementation in a single file with at most 80 lines of code.  
- Perform exactly one evaluation sink per request.  
- Do not perform any network operations beyond handling the incoming request.  
- Do not store or persist the expression string beyond processing it.