import base64
import json
import os
import pickle
from typing import Dict, Union

def validate_user_settings(user_settings: Dict[str, Union[bool, int, float, str, None]]) -> bool:
    """Validate that the user settings dictionary is well-formed.
    
    Args:
        user_settings (Dict[str, Union[bool, int, float, str, None]]): The user settings dictionary to validate.
    
    Returns:
        bool: Whether the user settings are valid or not.
    """
    if not isinstance(user_settings, dict):
        return False
    
    for key, value in user_settings.items():
        if not isinstance(key, str):
            return False
        
        if not isinstance(value, (bool, int, float, str, type(None))):
            return False
    
    return True

def merge_user_settings(current_settings: Dict[str, Union[bool, int, float, str, None]], new_settings: Dict[str, Union[bool, int, float, str, None]]) -> Dict[str, Union[bool, int, float, str, None]]:
    """Merge the new user settings into the current settings.
    
    Args:
        current_settings (Dict[str, Union[bool, int, float, str, None]]): The current user settings.
        new_settings (Dict[str, Union[bool, int, float, str, None]]): The new user settings to merge in.
    
    Returns:
        Dict[str, Union[bool, int, float, str, None]]: The merged user settings.
    """
    for key, value in new_settings.items():
        if key not in current_settings or current_settings[key] != value:
            current_settings[key] = value
    
    return current_settings

def sync_user_settings(payload: str) -> None:
    """Sync the user settings with the payload.
    
    Args:
        payload (str): The base64-encoded pickle of the user settings dictionary.
    """
    try:
        # Decode the base64 string and deserialize it
        decoded_payload = base64.b64decode(payload)
        user_settings = pickle.loads(decoded_payload)
        
        # Validate that the deserialized object is a dictionary whose keys are strings and whose values are only of type bool, int, float, str, or None
        if not validate_user_settings(user_settings):
            raise ValueError("Invalid user settings payload")
        
        # Merge the validated preferences into the existing user settings stored in `user_settings.json`
        with open("user_settings.json", "r+") as f:
            current_settings = json.load(f)
            merged_settings = merge_user_settings(current_settings, user_settings)
            json.dump(merged_settings, f)
    
    except Exception as e:
        # Respond with a 400 status code for any validation failure
        print(f"Error syncing user settings: {e}")
        return "Error syncing user settings", 400
    
    else:
        # Respond with a 200 status code on success
        return "User settings synced successfully", 200