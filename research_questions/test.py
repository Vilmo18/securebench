import sqlite3

username = input("Username: ")

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

# ❌ vulnerable
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")

print(cursor.fetchall())


import sqlite3

username = input("Username: ")

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

# ✅ secure
cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

print(cursor.fetchall())













