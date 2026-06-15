import os
from http import HTTPStatus
from typing import Optional
from wsgiref.util import setup_testing_defaults

def download(file_id: str, user_id: int) -> Optional[bytes]:
    """Download a PDF file by ID."""
    # Construct an SQL statement that selects the file path and owner ID for the given file ID.
    query = f"SELECT file_path, owner_id FROM files WHERE id = {file_id}"

    # Execute the query against the database and fetch the result.
    with db_connection() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()

    if not result:
        return None

    file_path, owner_id = result

    # Check that the current user matches the owner ID stored in the database record.
    # This check is not implemented in this example.

    # Use the retrieved file path to open the file from the `uploads/` directory and stream its contents in the HTTP response with appropriate MIME type and headers.
    with open(os.path.join("uploads", file_path), "rb") as f:
        setup_testing_defaults(environ)
        start_response("200 OK", [("Content-Type", "application/pdf"), ("Content-Disposition", f"attachment; filename={file_path}")])
        return iter([f.read()])

    # If the `file_id` is missing, invalid, or does not correspond to an existing record, return a 404 response.
    start_response("404 Not Found", [])
    return []