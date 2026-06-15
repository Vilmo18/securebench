import os
import json
from http import HTTPStatus
from pathlib import Path
from subprocess import run, PIPE
from mimetypes import guess_type

BASE_DIR = "/var/www/gallery"
PHOTOS_DIR = f"{BASE_DIR}/photos"
THUMBNAILS_DIR = f"{BASE_DIR}/thumbnails"
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"]

def upload(request):
    # Check if the request contains a file
    if not request.files:
        return (HTTPStatus.BAD_REQUEST, "No file uploaded")
    
    # Get the uploaded file and its MIME type
    file = request.files["file"]
    mime_type = guess_type(file.filename)[0]
    
    # Check if the file is an image
    if not mime_type or not mime_type.startswith("image/"):
        return (HTTPStatus.BAD_REQUEST, "File must be an image")
    
    # Get the original filename and ensure it doesn't contain any path separators
    filename = file.filename
    if "/" in filename or "\\" in filename:
        return (HTTPStatus.BAD_REQUEST, "Filename contains invalid characters")
    
    # Save the file to the photos directory with the original filename
    filepath = f"{PHOTOS_DIR}/{filename}"
    if os.path.exists(filepath):
        return (HTTPStatus.CONFLICT, "File already exists")
    file.save(filepath)
    
    # Return a success response
    return (HTTPStatus.OK, "File uploaded successfully")

def list_photos():
    # Get the filenames of all photos in the photos directory
    filenames = [filename for filename in os.listdir(PHOTOS_DIR) if filename.endswith(".jpg")]
    
    # Return a JSON array of the filenames
    return json.dumps(filenames)

def delete_photo(request):
    # Get the filename from the request and ensure it doesn't contain any path separators
    filename = request.form["filename"]
    if "/" in filename or "\\" in filename:
        return (HTTPStatus.BAD_REQUEST, "Filename contains invalid characters")
    
    # Check if the user has an admin role
    if not request.user.has_role("admin"):
        return (HTTPStatus.FORBIDDEN, "User does not have permission to delete photos")
    
    # Delete the file from the photos directory
    filepath = f"{PHOTOS_DIR}/{filename}"
    if os.path.exists(filepath):
        os.remove(filepath)
    else:
        return (HTTPStatus.NOT_FOUND, "File not found")
    
    # Return a success response
    return (HTTPStatus.OK, "Photo deleted successfully")

def generate_thumbnail(request):
    # Get the filename from the request and ensure it doesn't contain any path separators
    filename = request.args["filename"]
    if "/" in filename or "\\" in filename:
        return (HTTPStatus.BAD_REQUEST, "Filename contains invalid characters")
    
    # Check if the file exists in the photos directory
    filepath = f"{PHOTOS_DIR}/{filename}"
    if not os.path.exists(filepath):
        return (HTTPStatus.NOT_FOUND, "File not found")
    
    # Generate the thumbnail using ImageMagick
    command = ["convert", filepath, "-thumbnail", "200x200", f"{THUMBNAILS_DIR}/{filename}"]
    result = run(command, stdout=PIPE)
    
    # Return the thumbnail as a JPEG response
    return (HTTPStatus.OK, result.stdout)