import http.server
import sqlite3
from urllib.parse import urlparse, parse_qs
import html

DB_NAME = 'users.db'

def get_user_profile(username):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        query = """
            SELECT display_name, bio,
                   (SELECT GROUP_CONCAT(title || ':' || content, '|')
                    FROM posts
                    WHERE posts.user_id = users.id
                    ORDER BY created_at DESC
                    LIMIT 10) as recent_posts
            FROM users
            WHERE username = ?
        """

        cursor.execute(query, (username,))
        result = cursor.fetchone()

        if not result:
            return None

        display_name, bio, posts_data = result
        recent_posts = []
        if posts_data:
            recent_posts = [post.split(':') for post in posts_data.split('|')]

        conn.close()
        return {
            'display_name': display_name,
            'bio': bio,
            'recent_posts': recent_posts
        }
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

def generate_html(profile):
    if not profile:
        return """
        <html>
            <head><title>Profile Not Found</title></head>
            <body>
                <h1>Profile Not Found</h1>
                <p>The requested user profile was not found.</p>
            </body>
        </html>
        """

    display_name = html.escape(profile['display_name'])
    bio = html.escape(profile['bio'])

    posts_html = ''.join(
        f"<li><b>{html.escape(post[0])}</b> {html.escape(post[1])}</li>"
        for post in profile['recent_posts']
    )

    return f"""
    <html>
        <head><title>{display_name}'s Profile</title></head>
        <body>
            <h1>{display_name}</h1>
            <p>{bio}</p>
            <ul>
                {posts_html}
            </ul>
        </body>
    </html>
    """

class RequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        username = query_params.get('username', [None])[0]
        if not username:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Username parameter is required.")
            return

        profile = get_user_profile(username)
        html_content = generate_html(profile)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())

def run(server_class=http.server.HTTPServer, handler_class=RequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print("Starting httpd server on port 8000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()