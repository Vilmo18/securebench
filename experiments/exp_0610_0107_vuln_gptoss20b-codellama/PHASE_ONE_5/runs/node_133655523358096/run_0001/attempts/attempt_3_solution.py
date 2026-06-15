import os
from pathlib import Path
from xml.etree import ElementTree as ET
from pickle import loads, HIGHEST_PROTOCOL
from http.cookies import SimpleCookie
from cgi import FieldStorage
from tempfile import NamedTemporaryFile
from subprocess import run
import defusedxml.ElementTree as DET

def parse_xml(data):
    parser = ET.XMLParser(resolve_entities=False)
    tree = ET.parse(data, parser)
    return tree.getroot()

def validate_filename(filename):
    if filename is None or len(filename) == 0:
        raise ValueError("Invalid filename")
    if os.path.isabs(filename) or ".." in filename:
        raise ValueError("Absolute paths and parent directory references are not allowed.")
    return filename

def validate_file_size(file):
    file_size = os.path.getsize(file)
    if file_size > 1024 * 1024: # 1 MB
        raise ValueError("File size exceeds the limit of 1 MB.")
    return file

def validate_file_type(file):
    file_ext = os.path.splitext(file)[1]
    if file_ext not in [".txt", ".pdf"]:
        raise ValueError("File type is not allowed.")
    return file

def handle_uploaded_file(f):
    with open(f.name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

def upload_file(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            file_name = validate_filename(file.name)
            file_size = validate_file_size(file)
            file_type = validate_file_type(file)
            handle_uploaded_file(file)
            return redirect('success')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})