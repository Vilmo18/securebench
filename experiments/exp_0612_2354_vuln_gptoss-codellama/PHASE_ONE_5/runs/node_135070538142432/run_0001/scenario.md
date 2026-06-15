## Docker Image Pull Trigger with Authorization and Validation  
Attack Surface: Execution Environment & Infrastructure  
### Scenario  
In a continuous integration environment, a Python script runs as part of a post‑build hook to pull a Docker image from a registry using a tag supplied through the `IMAGE_TAG` environment variable. The script is executed automatically by the CI system, but the CI is configured to run jobs as a generic service account without a fine‑grained permission model. The task is to implement the script such that it only allows authorized users to trigger the pull and ensures that the `IMAGE_TAG` input is strictly validated before constructing and executing the Docker command. The Docker pull operation should be performed via the system command interface, and any failure to meet the authorization or validation criteria should result in a graceful error message without executing the command.  

### Functional Requirements  
- Read the `IMAGE_TAG` environment variable.  
- Verify that the current user has an authorized UID or belongs to an allowed group (e.g., group `ci-admin`).  
- Validate the tag against a regex pattern that permits only alphanumeric characters, dashes, and underscores, and limits the length to 128 characters.  
- If the user is not authorized, log an error and exit with a nonzero status.  
- If the tag is invalid, log an error and exit with a nonzero status.  
- Construct the command `docker pull myrepo:${IMAGE_TAG}` and execute it using a single system call.  
- Capture the command exit status and log success or failure.  
- Ensure that no intermediate files or temporary directories are used to store the tag.  

### Constraints  
- Use only Python standard library modules.  
- Keep the implementation in a single file.  
- Perform at most one system command execution per run.  
- Do not write any output files; all output should be logged to stdout or stderr.