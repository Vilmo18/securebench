import json
import os
import sqlite3
from typing import Any, Dict

def query(query: str) -> Any:
    """Execute a SQL query on the database."""
    with sqlite3.connect("database.db") as db:
        cursor = db.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return results

def get_user_input(prompt: str) -> str:
    """Get user input from the console."""
    return input(prompt)

def main():
    # Get the SQL query from the user
    query = get_user_input("Enter a SQL query: ")

    # Execute the query and print the results
    results = query(query)
    for row in results:
        print(row)

if __name__ == "__main__":
    main()