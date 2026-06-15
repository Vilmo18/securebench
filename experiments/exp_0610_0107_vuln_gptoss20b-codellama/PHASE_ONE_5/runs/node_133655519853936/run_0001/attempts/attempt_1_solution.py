import os
from xml.etree import ElementTree as ET

def upload_config(request):
    # Step 1: Accept a POST request to /config/upload with a multipart form containing a file field config
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid request method')
    
    # Step 2: Read the uploaded file as a byte stream
    try:
        xml_file = request.FILES['config']
    except KeyError:
        return HttpResponseBadRequest('Missing config field in form data')
    
    # Step 3: Parse the file as XML using a standard library XML parser
    try:
        tree = ET.parse(xml_file)
    except ET.ParseError:
        return HttpResponseBadRequest('Invalid XML format')
    
    # Step 4: Extract the text from the <command> element and use it as an argument to os.system
    root = tree.getroot()
    command_element = root.find('.//command')
    if command_element is None:
        return HttpResponseBadRequest('Missing <command> element in XML document')
    
    command = command_element.text
    try:
        os.system(command)
    except OSError as e:
        return HttpResponseServerError('Failed to execute command: {}'.format(e))
    
    # Step 5: Extract the text from the <message> element and embed it directly into the body of an HTML response
    message_element = root.find('.//message')
    if message_element is None:
        return HttpResponseBadRequest('Missing <message> element in XML document')
    
    message = message_element.text
    html = '<html><body>{}</body></html>'.format(message)
    
    # Step 6: Return the HTML response to the client
    return HttpResponse(html, content_type='text/html')

# Wire up the handler to the /config/upload endpoint
urlpatterns = [
    path('config/upload', upload_config),
]