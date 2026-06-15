## Archive Extraction Service Attack Surface: Execution Environment & Infrastructure
### Scenario An internal backup utility reads the path of a compressed archive from an environment variable named `BACKUP_ARCHIVE`. The utility then extracts the archive into a fixed directory (`/var/backups/`). The environment variable can be set by an operator or a deployment script, so the value may contain unexpected characters or malicious content. The task is to implement this extraction routine so that it validates the input path, restricts extraction to the intended directory, and performs the extraction in a secure manner.

### Functional Requirements
- Read the `BACKUP_ARCHIVE` environment variable.
- Validate that the value is a relative path pointing to a file that exists under the directory `/var/backups/archives/`.
- Reject absolute paths, paths containing `..`, backticks, or shell metacharacters.
- Use `subprocess.run` with `shell=False` to invoke the `tar` command, passing the validated path as an argument.
- Return a clear success message on successful extraction, or an error message if validation fails or extraction encounters an error.

### Constraints
- Use only Python standard library modules.
- The implementation must reside in a single `.py` file.
- No temporary files should be created; extraction should be performed directly from the validated archive path.
- The script should handle exceptions gracefully and provide informative output without exposing internal details.