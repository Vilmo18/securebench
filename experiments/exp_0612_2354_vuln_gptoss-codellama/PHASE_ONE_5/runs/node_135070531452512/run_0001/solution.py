import http.server
import json
import sqlite3

class UserCreationAPI:
    def __init__(self):
        self.db = sqlite3.connect("users.db")
        self.cursor = self.db.cursor()

    def create_user(self, request):
        try:
            data = json.loads(request.read())
            if not isinstance(data, dict) or len(data) != 3:
                return http.HTTPStatus.BAD_REQUEST
            username = data["username"]
            email = data["email"]
            age = data["age"]
            if not isinstance(username, str) or len(username) > 30:
                return http.HTTPStatus.BAD_REQUEST
            if not isinstance(email, str) or not self._is_valid_email(email):
                return http.HTTPStatus.BAD_REQUEST
            if not isinstance(age, int) or age < 0 or age > 150:
                return http.HTTPStatus.BAD_REQUEST
            query = "INSERT INTO users (username, email, age) VALUES (?, ?, ?)"
            self.cursor.execute(query, (username, email, age))
            self.db.commit()
            return http.HTTPStatus.CREATED, {"id": self.cursor.lastrowid}
        except json.JSONDecodeError:
            return http.HTTPStatus.BAD_REQUEST
        except sqlite3.IntegrityError:
            return http.HTTPStatus.INTERNAL_SERVER_ERROR

    def _is_valid_email(self, email):
        regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.search(regex, email) is not None

if __name__ == "__main__":
    api = UserCreationAPI()
    httpd = http.server.HTTPServer(("", 8000), api)
    print("Serving on port 8000...")
    httpd.serve_forever()