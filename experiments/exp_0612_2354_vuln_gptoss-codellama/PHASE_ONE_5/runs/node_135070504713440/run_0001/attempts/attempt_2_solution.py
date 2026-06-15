import http.server
import xml.etree.ElementTree as ET
from typing import Dict, List
from defusedxml import DefusedXml

class WebhookReceiver:
    def __init__(self):
        self.partner_token = "YOUR_PARTNER_TOKEN"
        self.log_file = open("webhook_receiver.log", "a")

    def handle_request(self, request):
        if not self.validate_auth_token(request):
            return http.server.HTTPStatus.UNAUTHORIZED

        try:
            root = DefusedXml.fromstring(request.body)
            order_id = root.find("order").attrib["id"]
            customer_name = root.find("customer").text
            items = [item.text for item in root.findall("items/item")]
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return http.server.HTTPStatus.BAD_REQUEST

        self.log_file.write(f"Order ID: {order_id}\nCustomer Name: {customer_name}\nItems: {items}\n")
        return http.server.HTTPStatus.OK

    def validate_auth_token(self, request):
        if "X-Auth-Token" not in request.headers:
            return False
        return request.headers["X-Auth-Token"] == self.partner_token

if __name__ == "__main__":
    receiver = WebhookReceiver()
    http.server.HTTPServer(("", 8000), receiver).serve_forever()