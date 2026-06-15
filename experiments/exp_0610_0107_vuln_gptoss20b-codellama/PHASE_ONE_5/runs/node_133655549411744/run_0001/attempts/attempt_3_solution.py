import json
from xml.etree import ElementTree as ET
from urllib.parse import unquote
from defusedxml import defuse_stdlib, DefusedElementTree

def profile_view(request):
    # Deserialize the JSON payload without executing arbitrary code
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest()
    
    # Extract the XML string from the `profile_data` field
    try:
        xml_string = unquote(data["profile_data"])
    except KeyError:
        return HttpResponseBadRequest()
    
    # Parse the XML using a parser that disables external entity resolution and DTD processing
    defuse_stdlib()
    root = DefusedElementTree.fromstring(xml_string)
    
    # Retrieve the `name` element and the `avatar` element (URL) from the XML
    name = root.find("name").text
    avatar = root.find("avatar").get("src")
    
    # Render an HTML response that includes the user's name in a heading and the avatar image using an `<img>` tag
    return HttpResponse(f"<h1>{name}</h1><img src='{avatar}'>")