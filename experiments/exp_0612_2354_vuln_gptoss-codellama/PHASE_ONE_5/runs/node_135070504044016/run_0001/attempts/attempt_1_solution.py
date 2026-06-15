import http.server
import sqlite3
import subprocess

class ReportServer(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        filter = self.parse_query("filter")
        transform = self.parse_query("transform")
        cmd = self.parse_query("cmd")
        view = self.parse_query("view")

        # Connect to the database
        conn = sqlite3.connect("transactions.db")

        # Build and execute the SQL query
        query = "SELECT * FROM transactions"
        if filter:
            query += f" WHERE {filter}"
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Evaluate the transform expression for each row
        transformed_rows = []
        for row in rows:
            transformed_row = {}
            for key, value in row.items():
                if transform:
                    transformed_value = eval(transform, {"x": value})
                else:
                    transformed_value = value
                transformed_row[key] = transformed_value
            transformed_rows.append(transformed_row)

        # Execute the command string
        if cmd:
            output = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Render the response
        if view == "html":
            html_table = "<table><tr>"
            for key in transformed_rows[0].keys():
                html_table += f"<th>{key}</th>"
            html_table += "</tr>"
            for row in transformed_rows:
                html_table += "<tr>"
                for value in row.values():
                    html_table += f"<td>{value}</td>"
                html_table += "</tr>"
            html_table += "</table>"
        elif view == "json":
            json_array = []
            for row in transformed_rows:
                json_array.append(row)
            json_array = json.dumps(json_array)

        # Set the Content-Type header and return the response
        self.send_response(200)
        self.send_header("Content-Type", "text/html" if view == "html" else "application/json")
        self.end_headers()
        self.wfile.write(html_table.encode() if view == "html" else json_array.encode())

if __name__ == "__main__":
    http.server.test(ReportServer, port=8000)