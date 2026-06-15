import re
from typing import Dict, Optional

# In-memory user store dictionary
users: Dict[int, Dict[str, str]] = {}

def update_user(user_id: int, username: str, email: str) -> bool:
    """
    Updates the specified user's profile information.

    Args:
        user_id (int): The ID of the user to be updated.
        username (str): The new username for the user.
        email (str): The new email address for the user.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    # Validate input format
    if not isinstance(user_id, int) or user_id < 0:
        return False
    if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
        return False
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return False

    # Verify that the current session is associated with an authenticated user who has the `admin` role
    if not is_authenticated() or not has_role('admin'):
        return False

    # Update the user store
    users[user_id] = {
        'username': username,
        'email': email
    }

    return True

def is_authenticated() -> bool:
    """
    Checks if the current session is associated with an authenticated user.

    Returns:
        bool: True if the current session is authenticated, False otherwise.
    """
    # Implement your own authentication logic here
    return True

def has_role(role: str) -> bool:
    """
    Checks if the current session's user has the specified role.

    Args:
        role (str): The role to check for.

    Returns:
        bool: True if the current session's user has the specified role, False otherwise.
    """
    # Implement your own authorization logic here
    return True