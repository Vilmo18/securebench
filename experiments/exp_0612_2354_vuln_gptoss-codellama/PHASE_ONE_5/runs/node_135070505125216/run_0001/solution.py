import xml.etree.ElementTree as ET
from http import HTTPStatus
from typing import Optional
from defusedxml import DefusedXml

class ExternalXMLImportService:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def handle_request(self, request_body: bytes, headers: dict[str, str]) -> tuple[HTTPStatus, Optional[dict[str, str]]]:
        if not self.validate_api_key(headers):
            return HTTPStatus.UNAUTHORIZED, None

        try:
            root = DefusedXml.fromstring(request_body)
        except ET.ParseError as e:
            print(f"Failed to parse XML: {e}")
            return HTTPStatus.BAD_REQUEST, None

        resource_path = root.find("resourcePath").text
        if not self.validate_resource_path(resource_path):
            return HTTPStatus.BAD_REQUEST, None

        file_contents = self.read_file(resource_path)
        if file_contents is None:
            return HTTPStatus.NOT_FOUND, None

        self.store_file_contents(file_contents)
        return HTTPStatus.OK, {"message": "File successfully imported"}

    def validate_api_key(self, headers: dict[str, str]) -> bool:
        api_key = headers.get("X-API-Key")
        return api_key == self._api_key if api_key is not None else False

    def validate_resource_path(self, resource_path: str) -> bool:
        allowed_directory = "/data/resources"
        resolved_path = f"{allowed_directory}/{resource_path}"
        return os.path.realpath(resolved_path).startswith(allowed_directory)

    def read_file(self, file_path: str) -> Optional[str]:
        try:
            with open(file_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def store_file_contents(self, contents: str) -> None:
        # Implement your own logic to store the file contents in an internal data store
        pass