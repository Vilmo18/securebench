import os
from pathlib import Path

def get_avatar(user_id):
    avatars_dir = Path("avatars")
    user_id = user_id.strip()
    if not user_id:
        return None
    file_path = avatars_dir / f"{user_id}.png"
    if not file_path.exists():
        return None
    with open(file_path, "rb") as f:
        data = f.read()
    return data